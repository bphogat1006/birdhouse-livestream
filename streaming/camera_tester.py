from time import time, sleep
from camera_handler import get_stream_frame

frames = 0
start = time()
print('starting loop')
while 1:
    get_stream_frame()
    
    # fps counter
    frames += 1
    if frames == 30:
        elapsed = time()-start
        print('fps', frames/elapsed)
        frames = 0
        start = time()

