from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FfmpegOutput
from libcamera import controls, Transform
import cv2
from time import time
import multiprocessing as mp


class Camera:
    captures_folder = 'static/captures/'

    def __init__(self, camera_is_recording: mp.Value):
        self.picam2 = Picamera2()
        fps = 200
        height_main = 1080
        height_lores = 432
        aspect_ratio = 16/9
        size_main = (int(height_main*aspect_ratio), height_main)
        size_lores = (int(height_lores*aspect_ratio), height_lores)

        self.config = self.picam2.create_video_configuration(
            main={
                'size': size_main,
                'format': 'RGB888'
            },
            lores={
                'size': size_lores,
                'format': 'YUV420' # default
            },
            encode='main',
            transform=Transform(vflip=True, hflip=True),
            controls={
                'AfMode': controls.AfModeEnum.Manual,
                'AfRange': controls.AfRangeEnum.Full,
                'LensPosition': 2,
                'FrameDurationLimits': [int(1/fps*1000000), int(1/fps*1000000)]
            },
            buffer_count=1
        )
        self.picam2.align_configuration(self.config)
        self.picam2.configure(self.config)
        self.picam2.start()
        self.__encoder = H264Encoder()
        self.__recording = camera_is_recording
        self.__recording_start = None
        self.__max_recording_duration = 60*10 # 10 minutes

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
    
if __name__ == '__main__':
    cam = Camera(None)
    print(cam.config)
    size_main = cam.capture_main().shape
    size_lores = cam.capture_lores().shape
    print(size_main, size_lores)
