import os
import re
import time
from threading import Lock
from flask import Flask, request, render_template, Response, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from camera_handler import get_stream_frame, capture_image, toggle_recording, camera_is_recording, adjust_focus, camera_focus_value
from camera_setup import Camera


app = Flask(__name__, static_folder='static', template_folder='templates')
auth = HTTPBasicAuth()
users = {
    "poonga": generate_password_hash("bird"),
}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

filename_pattern = r'(.+\/)+(\w+)_(\d+).(jpg|mp4)'
def filename_regex(filename):
    result = re.search(filename_pattern, filename)
    return {
        'description': result.group(2),
        'timestamp': result.group(3),
        'extension': result.group(4)
    }

@app.route('/')
@auth.login_required
def index():
    images = []
    videos = []
    capture_files = [Camera.captures_folder+file for file in os.listdir(Camera.captures_folder)]
    capture_files.sort(key=lambda x: filename_regex(x)['timestamp'])
    capture_files.reverse()
    for filename in capture_files:
        timestamp = filename_regex(filename)['timestamp']
        date_string = (time.strftime('%a %b %d, %I:%M:%S %p', time.localtime(int(timestamp))))
        if '.jpg' in filename:
            images.append({
                'filename': filename,
                'date': date_string
            })
        else:
            videos.append({
                'filename': filename,
                'date': date_string,
                'description': filename_regex(filename)['description']
            })
    return render_template('stream.html', images=images, videos=videos, is_recording=camera_is_recording.value, camera_focus_value=camera_focus_value.value)

get_frame_lock = Lock()
def camera_frames_gen():
    while True:
        with get_frame_lock:
            frame = get_stream_frame()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/stream')
def stream():
    return Response(camera_frames_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/record', methods=['POST'])
def record():
    toggle_recording()
    time.sleep(1)
    return redirect(url_for('index'))

@app.route('/video', methods=['GET', 'POST'])
def view_video():
    if request.method == 'GET':
        if 'v' not in request.args.keys():
            return Response("'v' arg is missing", status=400)
        filename = request.args.get('v')
        description = filename_regex(filename)['description']
        return render_template('video.html', filename=filename, description=description)
    else:
        old_filename = request.form.get('filename')
        description = request.form.get('description')
        replacement = Camera.captures_folder + description + r'_\3.\4'
        new_filename = sub = re.sub(filename_pattern, replacement, old_filename)
        os.rename(old_filename, new_filename)
        return redirect(url_for('index'))

@app.route('/take_picture', methods=['POST'])
def take_picture():
    capture_image()
    time.sleep(1)
    return redirect(url_for('index'))

@app.route('/picture')
def view_picture():
    if 'v' not in request.args.keys():
        return Response("'v' arg is missing", status=400)
    filename = request.args.get('v')
    return render_template('image.html', filename=filename)

@app.route('/delete', methods=['POST'])
def delete_capture():
    filename = request.form.get('filename')
    os.remove(filename)
    return redirect(url_for('index'))

@app.route('/focus', methods=['POST'])
def focus():
    value = float(request.data)
    adjust_focus(value)
    return Response(status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)