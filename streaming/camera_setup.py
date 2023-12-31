from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FfmpegOutput
from libcamera import controls, Transform
import cv2
import os
from time import time
import multiprocessing as mp


CAMERA_FPS = int(os.environ['CAMERA_FPS'])
CAMERA_DEFAULT_FOCUS = float(os.environ['CAMERA_DEFAULT_FOCUS'])
MAX_RECORDING_DURATION = int(os.environ['MAX_RECORDING_DURATION'])

class Camera:
    captures_folder = 'static/captures/'
    size_main = (1080, 1920, 3)
    size_lores = (432, 768, 3)

    def __init__(self, camera_is_recording: mp.Value):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_video_configuration(
            main={
                'size': [Camera.size_main[1], Camera.size_main[0]],
                'format': 'RGB888'
            },
            lores={
                'size': [Camera.size_lores[1], Camera.size_lores[0]],
                'format': 'YUV420' # default
            },
            encode='main',
            transform=Transform(vflip=True, hflip=True),
            controls={
                'AfMode': controls.AfModeEnum.Manual,
                'AfRange': controls.AfRangeEnum.Full,
                'LensPosition': CAMERA_DEFAULT_FOCUS,
                'FrameDurationLimits': [int(1/CAMERA_FPS*1000000), int(1/CAMERA_FPS*1000000)]
            },
            buffer_count=1
        )
        self.picam2.align_configuration(self.config)
        self.picam2.configure(self.config)
        self.picam2.start()
        self.__encoder = H264Encoder()
        self.__recording = camera_is_recording
        self.__recording_start = None
        self.__max_recording_duration = 60 * MAX_RECORDING_DURATION # in seconds

    def capture_main(self):
        request = self.picam2.capture_request()
        frame = request.make_array('main')
        request.release()
        return frame

    def capture_lores(self):
        request = self.picam2.capture_request()
        frame = request.make_array('lores')
        request.release()
        frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB) # lores is in YUV420 format
        return frame
    
    def toggle_recording(self):
        if self.__recording.value:
            self.picam2.stop_encoder()
        else:
            self.__recording_start = time()
            filename = Camera.captures_folder + f'unnamed_{round(time())}.mp4'
            output = FfmpegOutput(filename)
            self.picam2.start_encoder(self.__encoder, output, quality=Quality.LOW)

        self.__recording.value = not self.__recording.value

    def recording_auto_cutoff(self):
        if not self.__recording.value:
            return
        duration = time() - self.__recording_start
        if duration > self.__max_recording_duration:
            self.toggle_recording()

    def adjust_focus(self, value):
        value = min(35, max(0, value))
        self.picam2.set_controls({"LensPosition": value})
    
if __name__ == '__main__':
    cam = Camera(None)
    print(cam.config)
    size_main = cam.capture_main().shape
    size_lores = cam.capture_lores().shape
    print(size_main, Camera.size_main)
    print(size_lores, Camera.size_lores)
