import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn
from src.video_processor import VideoProcessor
import tempfile
import aiofiles
from pathlib import Path
from datetime import datetime

load_dotenv()

app = FastAPI(title="Smart Vision Assistant")
video_processor = VideoProcessor()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the upload form"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Processing Assistant</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .upload-container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .upload-form {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            .progress {
                display: none;
                margin-top: 20px;
            }
            #results {
                margin-top: 20px;
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
        <div class="upload-container">
            <h1>Video Processing Assistant</h1>
            <p>Upload a video file to process it frame by frame.</p>
            <div class="upload-form">
                <input type="file" id="video" accept="video/*" />
                <button onclick="uploadVideo()">Upload & Process Video</button>
            </div>
            <div class="progress" id="progress">
                <h3>Processing...</h3>
                <p id="status"></p>
            </div>
            <div id="results"></div>
        </div>

        <script>
        async function uploadVideo() {
            const fileInput = document.getElementById('video');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a video file');
                return;
            }

            const formData = new FormData();
            formData.append('video', file);

            document.getElementById('progress').style.display = 'block';
            document.getElementById('status').textContent = 'Uploading video...';
            document.getElementById('results').textContent = '';

            try {
                const response = await fetch('/upload/video', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (result.status === 'success') {
                    document.getElementById('status').textContent = 'Processing complete!';
                    document.getElementById('results').textContent = JSON.stringify(result.results, null, 2);
                } else {
                    document.getElementById('status').textContent = 'Error: ' + result.message;
                }
            } catch (error) {
                document.getElementById('status').textContent = 'Error: ' + error.message;
            }
        }
        </script>
    </body>
    </html>
    """

@app.post("/upload/video")
async def upload_video(video: UploadFile = File(...)):
    """Handle video file upload and processing"""
    try:
        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, video.filename)
        
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await video.read()
            await out_file.write(content)

        results = []
        async for frame, metadata in video_processor.process_video(temp_path):
            results.append({
                "frame_number": metadata["frame_number"],
                "progress": metadata["progress_percent"],
                "frame_size": metadata["frame_size"]
            })
        
        # Cleanup temp file
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        return JSONResponse({
            "status": "success",
            "message": "Video processed successfully",
            "results": results
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/status")
async def get_status():
    """Health check endpoint"""
    return {"status": "running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
