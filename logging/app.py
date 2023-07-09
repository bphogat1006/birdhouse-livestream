from flask import Flask, Response, request
from motion_utils import get_db_connection, get_motion_data, NUM_DATA_CHUNKS
from threading import Thread
from time import time
from update_display import display_motion_data


# continuously update display with motion data
Thread(target=display_motion_data).start()

# flask
app = Flask(__name__)

@app.route('/')
def index():
    motion_data, motion_detected = get_motion_data(NUM_DATA_CHUNKS, get_db_connection())
    res = [str(motion_detected)] + [f'{str(i+1).zfill(2)}: {sum}<br>' for i,sum in enumerate(motion_data)]
    return Response(res)

@app.route('/log', methods=['POST'])
def log():
    # retrieve data
    motion_factor = float(request.data)
    
    # insert into db
    with get_db_connection() as conn:
        conn.execute('INSERT INTO motion_logs (time, motion) VALUES (?, ?)', (time(), motion_factor))

    return Response(status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
