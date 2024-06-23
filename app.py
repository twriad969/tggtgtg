from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import subprocess
import uuid
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
STATUS = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def download_video(url, file_path):
    response = requests.get(url, stream=True)
    with open(file_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    return file_path

def watermark_video(input_path, output_path, watermark_text):
    # Get video duration
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    duration = float(result.stdout)

    # Watermark the entire video if duration is less than 15 minutes, otherwise watermark every 15 minutes
    if duration <= 900:
        command = [
            'ffmpeg', '-i', input_path, '-vf',
            f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-th-10", output_path
        ]
    else:
        command = [
            'ffmpeg', '-i', input_path, '-vf',
            f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-th-10:enable='mod(t,900)'", output_path
        ]
    subprocess.run(command, check=True)

@app.route('/')
def index():
    return render_template('index.html', status=STATUS)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file_id + '_' + file.filename)
    file.save(file_path)
    output_path = os.path.join(PROCESSED_FOLDER, file_id + '_' + file.filename)
    watermark_text = request.form.get('watermark_text', 'Watermark')

    STATUS[file_id] = {'filename': file.filename, 'status': 'processing'}

    def process_video():
        watermark_video(file_path, output_path, watermark_text)
        STATUS[file_id]['status'] = 'completed'
        STATUS[file_id]['url'] = f'/processed/{file_id}_{file.filename}'

    subprocess.Popen(process_video)
    return jsonify({'id': file_id, 'status': STATUS[file_id]})

@app.route('/download', methods=['POST'])
def download_file():
    url = request.form['url']
    file_id = str(uuid.uuid4())
    filename = os.path.basename(url)
    file_path = os.path.join(UPLOAD_FOLDER, file_id + '_' + filename)
    download_video(url, file_path)
    output_path = os.path.join(PROCESSED_FOLDER, file_id + '_' + filename)
    watermark_text = request.form.get('watermark_text', 'Watermark')

    STATUS[file_id] = {'filename': filename, 'status': 'processing'}

    def process_video():
        watermark_video(file_path, output_path, watermark_text)
        STATUS[file_id]['status'] = 'completed'
        STATUS[file_id]['url'] = f'/processed/{file_id}_{filename}'

    subprocess.Popen(process_video)
    return jsonify({'id': file_id, 'status': STATUS[file_id]})

@app.route('/status/<file_id>')
def get_status(file_id):
    if file_id in STATUS:
        return jsonify(STATUS[file_id])
    return 'File ID not found', 404

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
