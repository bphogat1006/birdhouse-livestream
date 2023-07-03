import numpy as np
import multiprocessing as mp
import ctypes
import cv2
from time import time


# camera lores frame dimensions
lores_frame_shape = (432, 768, 3)

# background subtractor (motion detection)
backsub_frame_counter = 0
backsub_update_freq = 10
backsub_history = 3
backsub = cv2.createBackgroundSubtractorMOG2(detectShadows=False, history=backsub_history)

def trigger_backsub_update():
    global backsub_frame_counter
    trigger = backsub_frame_counter == 0
    backsub_frame_counter = (backsub_frame_counter+1) % backsub_update_freq
    return trigger

def get_stream_frame():
    # get frame and convert to usable format
    new_frame_event.wait()
    frame = np_frame.copy()
    new_frame_event.clear()
    
    # update backsub
    if trigger_backsub_update():
        # frame = process_backsub_frame(frame) # temp
        process_backsub_frame(frame)

    # return processed frame
    return compress_jpg(frame)

def process_backsub_frame(frame):
    frame = cv2.resize(frame, np.array([lores_frame_shape[1], lores_frame_shape[0]]) // 2, interpolation=cv2.INTER_NEAREST)
    frame = cv2.GaussianBlur(frame, (21, 21), 0)
    fgmask = backsub.apply(frame)
    motion_factor = ( np.sum(fgmask)/255 / np.prod(fgmask.shape) ) ** 0.25
    motion_percentage = round(motion_factor * 100)
    # print('#'*motion_percentage, '*'*(100-motion_percentage)) # temp
    # return fgmask # temp

def compress_jpg(frame):
    flag, encoded_img = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return bytearray(encoded_img)


# multiprocessing/camera stuff

# shared data
mp_frame = mp.Array(ctypes.c_ubyte, int(np.prod(lores_frame_shape)), lock=mp.Lock())
np_frame = np.frombuffer(mp_frame.get_obj(), dtype=ctypes.c_ubyte).reshape(lores_frame_shape)
# events
new_frame_event = mp.Event()
toggle_recording_event = mp.Event()
capture_image_event = mp.Event()
# values
camera_is_recording = mp.Value('B', lock=True) # 'B' = unsigned byte
camera_is_recording.value = False

# trigger camera events
def capture_image():
    capture_image_event.set()

def toggle_recording():
    toggle_recording_event.set()

# run all camera processes in separate process
def camera_process(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording):
    from camera import Camera
    import asyncio
    camera = Camera(camera_is_recording)

    async def event(mp_event: mp.Event):
        while 1:
            if mp_event.is_set():
                break
            await asyncio.sleep(0)

    async def streaming_loop():
        while 1:
            # Get the captured frame as a numpy array
            await asyncio.sleep(0)
            if new_frame_event.is_set():
                continue
            np_frame[:] = camera.capture_lores()
            new_frame_event.set()
    
    async def capture_image_loop():
        while 1:
            await event(capture_image_event)
            img = camera.capture_main()
            cv2.imwrite(camera.captures_folder + f'img_{round(time())}.jpg', img)
            capture_image_event.clear()
    
    async def capture_video_loop():
        while 1:
            await event(toggle_recording_event)
            camera.toggle_recording()
            toggle_recording_event.clear()
    
    async def video_cutoff_checker():
        while 1:
            camera.recording_auto_cutoff()
            await asyncio.sleep(10)

    async def main():
        asyncio.create_task(streaming_loop())
        asyncio.create_task(capture_image_loop())
        asyncio.create_task(capture_video_loop())
        asyncio.create_task(video_cutoff_checker())

        while 1:
            await asyncio.sleep(9999) # run forever

    asyncio.run(main())

# start camera process
mp.Process(target=camera_process, args=(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording)).start()
