import numpy as np
import multiprocessing as mp
import ctypes
import cv2
from time import time, sleep
from camera_setup import Camera


# retrieve camera frame encoded for streaming
def get_stream_frame():
    # get frame
    new_frame_event.wait()
    new_frame_event.clear()
    frame = np_frame.copy()
    
    # update backsub
    trigger_backsub_update()

    # return jpeg encoded frame
    flag, encoded_img = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return bytearray(encoded_img)


# multiprocessing/camera stuff

# shared data
mp_frame = mp.Array(ctypes.c_ubyte, int(np.prod(Camera.size_lores)), lock=mp.Lock())
np_frame = np.frombuffer(mp_frame.get_obj(), dtype=ctypes.c_ubyte).reshape(Camera.size_lores)
camera_is_recording = mp.Value('B', lock=True) # 'B' = unsigned byte
camera_is_recording.value = False

# events
new_frame_event = mp.Event()
toggle_recording_event = mp.Event()
capture_image_event = mp.Event()
update_backsub_event = mp.Event()

# trigger camera events
def capture_image():
    capture_image_event.set()

def toggle_recording():
    toggle_recording_event.set()

def trigger_backsub_update():
    update_backsub_event.set()

# function to run background subtraction (motion detection) in separate process
def motion_detection_process(update_backsub_event, np_frame):
    import requests
    
    def log_activity(motion_factor):
        # destination address to send activity log
        dest_url = 'http://127.0.0.1:3001/log'

        # send data
        try:
            r = requests.post(dest_url, str(motion_factor))
            print(r)
        except Exception as e:
            pass
    
    backsub_frame_counter = 0
    backsub_update_freq = 10 # every n frames
    backsub_history = 50
    backsub = cv2.createBackgroundSubtractorMOG2(detectShadows=False, history=backsub_history)
    
    while 1:
        # get camera frame
        new_frame_event.wait()
        new_frame_event.clear()
        frame = np_frame.copy()
        # apply frame to cv background subtractor
        frame = cv2.resize(frame, np.array([Camera.size_lores[1], Camera.size_lores[0]]) // 2, interpolation=cv2.INTER_NEAREST)
        frame = cv2.GaussianBlur(frame, (21, 21), 0)
        fgmask = backsub.apply(frame)
        
        # calculate amount of motion
        motion_factor = ( np.sum(fgmask)/255 / np.prod(fgmask.shape) ) # calculate ratio of white to black pixels
        motion_factor = motion_factor ** 0.25 # scale up smaller values
        log_activity(motion_factor)

        # debugging
        if 1:
            motion_percentage = round(motion_factor * 100)
            print('#'*motion_percentage, '*'*(100-motion_percentage))

        # delay
        sleep(0.5)

# function to run all camera capture functions in separate process
def camera_process(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording):
    from camera_setup import Camera
    import asyncio

    camera = Camera(camera_is_recording)

    async def event(mp_event: mp.Event):
        while 1:
            if mp_event.is_set():
                mp_event.clear()
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
    
    async def capture_video_loop():
        while 1:
            await event(toggle_recording_event)
            camera.toggle_recording()
    
    async def video_auto_cutoff_checker():
        while 1:
            camera.recording_auto_cutoff()
            await asyncio.sleep(10)

    async def main():
        asyncio.create_task(streaming_loop())
        asyncio.create_task(capture_image_loop())
        asyncio.create_task(capture_video_loop())
        asyncio.create_task(video_auto_cutoff_checker())

        while 1:
            await asyncio.sleep(9999) # run forever

    asyncio.run(main())

# start processes
mp.Process(target=motion_detection_process, args=(update_backsub_event, np_frame)).start()
mp.Process(target=camera_process, args=(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording)).start()
