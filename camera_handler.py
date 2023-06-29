import numpy as np
import multiprocessing as mp
import ctypes
import cv2
from time import time, sleep


lores_frame_shape = (432, 768, 3)

lores_frame_counter = 0
def trigger_backsub_update():
    global lores_frame_counter
    trigger = lores_frame_counter == 0
    lores_frame_counter = (lores_frame_counter+1) % 10
    return trigger

def camera_process(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording):
    from camera import Camera
    from threading import Thread
    camera = Camera(camera_is_recording)

    def streaming_loop():
        while 1:
            # Get the captured frame as a numpy array
            if new_frame_event.is_set():
                continue
            np_frame[:] = camera.capture_lores()
            new_frame_event.set()
    
    def capture_image_loop():
        while 1:
            capture_image_event.wait()
            img = camera.capture_main()
            cv2.imwrite(camera.captures_folder + f'img_{round(time())}.jpg', img)
            capture_image_event.clear()
    
    def video_loop():
        while 1:
            toggle_recording_event.wait()
            camera.toggle_recording()
            toggle_recording_event.clear()
    
    def video_checker():
        while 1:
            camera.recording_auto_cutoff()
            sleep(10)

    Thread(target=streaming_loop).start()
    Thread(target=capture_image_loop).start()
    Thread(target=video_loop).start()
    Thread(target=video_checker).start()

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
    return compress(frame)

def compress(frame):
    flag, encoded_img = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return bytearray(encoded_img)

def process_backsub_frame(frame):
    frame = cv2.GaussianBlur(frame, (21, 21), 0)
    fgmask = backSub.apply(frame)
    # return fgmask # temp

def capture_image():
    capture_image_event.set()

def toggle_recording():
    toggle_recording_event.set()


# background subtractor
backSub = cv2.createBackgroundSubtractorMOG2(detectShadows=False, history=150)

# multiprocessing
# shared data
mp_frame = mp.Array(ctypes.c_ubyte, int(np.prod(lores_frame_shape)), lock=mp.Lock())
np_frame = np.frombuffer(mp_frame.get_obj(), dtype=ctypes.c_ubyte).reshape(lores_frame_shape)
# events
new_frame_event = mp.Event()
toggle_recording_event = mp.Event()
capture_image_event = mp.Event()
# values
camera_is_recording = mp.Value('B', lock=True)
camera_is_recording.value = False

# start capture process
mp.Process(target=camera_process, args=(np_frame, new_frame_event, capture_image_event, toggle_recording_event, camera_is_recording)).start()
