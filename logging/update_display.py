from datetime import datetime
import digitalio
import board
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw, ImageFont
from motion_utils import get_db_connection, get_motion_data, NUM_DATA_CHUNKS


def display_motion_data():
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = None
    buttonA = digitalio.DigitalInOut(board.D23)
    buttonB = digitalio.DigitalInOut(board.D24)
    buttonA.switch_to_input()
    buttonB.switch_to_input()
    buttonAPressed = lambda: not buttonA.value
    buttonBPressed = lambda: not buttonB.value
    size = 240
    display = st7789.ST7789(
        board.SPI(),
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=64000000,
        width=size,
        height=size,
        x_offset=0,
        y_offset=80,
        rotation=180
    )
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = True
    image = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(image)

    def draw_rect(xywh, fill=None, outline=None):
        x, y, w, h = xywh
        x2 = x+w
        y2 = y+h
        draw.rectangle((x, y, x2, y2), fill, outline)

    while 1:
        # get data
        motion_data, recent_motion = get_motion_data(NUM_DATA_CHUNKS, get_db_connection())
        max_height = max(max(motion_data), 75)
        motion_data = [i/max_height for i in motion_data]

        # draw graph on display
        draw.rectangle((0, 0, size, size), fill=(0, 0, 0))
        x = 0
        y = 75
        w = size / NUM_DATA_CHUNKS
        for h in motion_data:
            draw_rect((x, y, w, -h*y), fill=(255, 255, 255), outline=None)
            x += w
        
        # draw x axis (time) under the graph
        hour = datetime.now().hour%12
        hours = [(hour+i*4-1)%12+1 for i in range(4)]
        for i, x in enumerate([x*(size/4+12) for x in range(4)]):
            draw.text((x, y), str(hours[i]), fill=(255, 255, 255), font=ImageFont.truetype('arial.ttf', size=20))

        # display banner if there has been any recent motion
        if 1:
            y = size/2 + 35
            draw_rect((0, y-45, size, 90), fill=(255,100,100))
            draw.multiline_text((size/2, y), 'MOTION\nDETECTED', anchor='mm', align='center', fill=(0,0,0), font=ImageFont.truetype('arial.ttf', size=40))

        # display time
        t = datetime.now().strftime('%I:%M %p')
        draw.text((size/2, size), t, fill=(255, 255, 255), anchor='ms', align='center', font=ImageFont.truetype('arial.ttf', size=30))

        # draw image to display
        display.image(image)