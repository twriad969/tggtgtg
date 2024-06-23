from flask import Flask, request, send_from_directory, render_template, jsonify
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
import os
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

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
    clip = VideoFileClip(input_path)
    duration = clip.duration
    watermark = (TextClip(watermark_text, fontsize=24, color='white', size=(clip.size[0], 30), bg_color='black')
                .set_position(('center', 'bottom'))
                .set_duration(15)
                .set_start(lambda t: t % 900 == 0))
    watermarked_clip = CompositeVideoClip([clip, watermark])
    watermarked_clip.write_videofile(output_path, codec='libx264')
    clip.close()
    watermarked_clip.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    output_path = os.path.join(PROCESSED_FOLDER, file.filename)
    watermark_text = request.form.get('watermark_text', 'Watermark')
    watermark_video(file_path, output_path, watermark_text)
    return jsonify({'url': f'/processed/{file.filename}'})

@app.route('/download', methods=['POST'])
def download_file():
    url = request.form['url']
    filename = os.path.basename(url)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    download_video(url, file_path)
    output_path = os.path.join(PROCESSED_FOLDER, filename)
    watermark_text = request.form.get('watermark_text', 'Watermark')
    watermark_video(file_path, output_path, watermark_text)
    return jsonify({'url': f'/processed/{filename}'})

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)