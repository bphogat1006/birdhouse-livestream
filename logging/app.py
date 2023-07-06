from flask import Flask, Response, request
import sqlite3
from motion_utils import generate_sums
from threading import Thread
from time import sleep, time


# constants
NUM_DATA_CHUNKS = 24
DB_NAME = 'bird.sqlite3'


# sqlite setup
def get_db_connection():
    return sqlite3.connect(DB_NAME)

with get_db_connection() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS motion_logs ( time FLOAT, motion FLOAT )')


# define threads

# continuously update display with motion data
def display_motion_data():
    while 1:
        # get data
        motion_data = generate_sums(NUM_DATA_CHUNKS, get_db_connection())
        print(motion_data)
        # TODO draw graph on display
        # delay
        sleep(10)

# continuously update time on display
def update_time():
    while 1:
        # TODO draw time on display
        sleep(1)

# start threads
Thread(target=display_motion_data).start()
Thread(target=update_time).start()


# flask
app = Flask(__name__)

@app.route('/log', methods=['POST'])
def log():
    # retrieve data
    motion_factor = float(request.data)
    
    # scale up smaller values
    # motion_factor = motion_factor ** 0.25

    # insert into db
    with get_db_connection() as conn:
        res = conn.execute('INSERT INTO motion_logs (time, motion) VALUES (?, ?)', (time(), motion_factor))

    print('motion_factor', motion_factor)
    return Response(status=200)

if __name__ == '__main__':
    app.run(port=3001)
