import os
import subprocess
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Global variable to store optimization progress
optimization_progress = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(file_path):
    """Get file size in MB"""
    return round(os.path.getsize(file_path) / (1024 * 1024), 2)

def optimize_video(input_path, output_path, task_id):
    """Optimize video using FFmpeg with lossless compression"""
    global optimization_progress
    
    try:
        # Get original file size
        original_size = get_file_size_mb(input_path)
        optimization_progress[task_id] = {
            'status': 'processing',
            'progress': 0,
            'original_size': original_size,
            'current_size': original_size,
            'message': 'Starting optimization...'
        }
        
        # FFmpeg command for lossless optimization
        # Using H.264 with high quality settings and efficient encoding
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',           # H.264 codec
            '-preset', 'veryslow',        # Slowest preset for best compression
            '-crf', '18',                 # Constant Rate Factor (18 is visually lossless)
            '-c:a', 'aac',                # AAC audio codec
            '-b:a', '128k',               # Audio bitrate
            '-movflags', '+faststart',    # Optimize for web streaming
            '-y',                         # Overwrite output file
            output_path
        ]
        
        # Run FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor progress
        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Update progress (simplified - in real app you'd parse FFmpeg output)
                if 'time=' in output:
                    optimization_progress[task_id]['progress'] += 1
                    if optimization_progress[task_id]['progress'] > 100:
                        optimization_progress[task_id]['progress'] = 100
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            # Optimization successful
            optimized_size = get_file_size_mb(output_path)
            compression_ratio = round((1 - optimized_size / original_size) * 100, 1)
            
            optimization_progress[task_id] = {
                'status': 'completed',
                'progress': 100,
                'original_size': original_size,
                'current_size': optimized_size,
                'compression_ratio': compression_ratio,
                'message': f'Optimization completed! Reduced by {compression_ratio}%',
                'output_file': os.path.basename(output_path)
            }
        else:
            # Optimization failed
            optimization_progress[task_id] = {
                'status': 'error',
                'progress': 0,
                'message': 'Optimization failed. Please check your video file.'
            }
            
    except Exception as e:
        optimization_progress[task_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Error during optimization: {str(e)}'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Save uploaded file
        input_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(input_path)
        
        # Generate output filename
        output_filename = f"{name}_optimized{ext}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Start optimization in background thread
        thread = threading.Thread(
            target=optimize_video,
            args=(input_path, output_path, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': 'Upload successful! Optimization started...'
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/progress/<task_id>')
def get_progress(task_id):
    if task_id in optimization_progress:
        return jsonify(optimization_progress[task_id])
    return jsonify({'error': 'Task not found'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(OUTPUT_FOLDER, filename),
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up old files"""
    try:
        # Clean uploads older than 1 hour
        current_time = time.time()
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.getctime(file_path) < current_time - 3600:  # 1 hour
                os.remove(file_path)
        
        # Clean outputs older than 24 hours
        for filename in os.listdir(OUTPUT_FOLDER):
            file_path = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.getctime(file_path) < current_time - 86400:  # 24 hours
                os.remove(file_path)
        
        return jsonify({'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 