"""
This file runs the backend for a simple read-aloud audio book recorder app.
It works as follows:
    - a user selects and uploads a .txt file that contains 1 sentence per line
    - the backend stores the 
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import glob
from zipfile import ZipFile
from io import BytesIO
import hashlib


app = Flask(__name__)
UPLOAD_FOLDER = 'audio_files'
TSV_FILE = 'audio_mapping.tsv'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LOCAL_SENTENCES_FILE = "last_uploaded_sentences.txt"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-sentences', methods=['POST'])
def upload():
    file = request.files['file']
    sentences = file.read().decode('utf-8').split('\n')
    sentences = [s.strip() for s in sentences if s.strip()]
    with open(LOCAL_SENTENCES_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sentences))
    return jsonify(sentences)

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    audio = request.files['audio']
    idx = request.form.get('sentence_idx', '0')
    sentence = request.form.get("sentence_text")
    md5hash = hashlib.md5(sentence.encode())
    filename = f"{md5hash.hexdigest()}.webm"

    path = os.path.join(UPLOAD_FOLDER, filename)
    audio.save(path)

    ## Update TSV with mapping (append if not present)
    # with open(LOCAL_SENTENCES_FILE, encoding='utf-8') as f:
    #     sentences = [s.strip() for s in f if s.strip()]
    # sentence = sentences[int(idx)] if int(idx) < len(sentences) else ""

    
    # Make sure mapping is unique and up-to-date
    mappings = {}
    if os.path.exists(TSV_FILE):
        with open(TSV_FILE, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) == 2:
                    mappings[parts[0]] = parts[1]
    mappings[filename] = sentence
    with open(TSV_FILE, 'w', encoding='utf-8') as f:
        for fn, sent in mappings.items():
            f.write(f"{fn}\t{sent}\n")
    
    return 'Audio received', 200

@app.route('/download-recordings')
def download_recordings():
    # Load mapping of audio files to sentences
    mappings = []
    if os.path.exists(TSV_FILE):
        with open(TSV_FILE, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) == 2 and os.path.exists(os.path.join(UPLOAD_FOLDER, parts[0])):
                    mappings.append((parts[0], parts[1]))

    tsv_content = "audio_filename\tsentence\n" + '\n'.join(f"{fn}\t{sent}" for fn, sent in mappings)
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        # Add audio files
        for filename, _ in mappings:
            zf.write(os.path.join(UPLOAD_FOLDER, filename), filename)
            os.remove(os.path.join(UPLOAD_FOLDER, filename))
        # Add TSV mapping
        zf.writestr("mapping.tsv", tsv_content)
    memory_file.seek(0)
    
    
    return send_file(memory_file, as_attachment=True, download_name='recordings.zip')

if __name__ == '__main__':
    app.run(debug=True)