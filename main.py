import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.video_processor import VideoProcessor
import tempfile
import aiofiles
from pathlib import Path
from datetime import datetime

load_dotenv()

app = FastAPI(title="Video Processing Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            .container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
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
            .button {
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            .button:hover {
                background: #0056b3;
            }
            .file-input {
                border: 2px dashed #ccc;
                padding: 20px;
                text-align: center;
                border-radius: 4px;
            }
            .search-container {
                margin-top: 20px;
            }
            .search-input {
                width: 100%;
                padding: 10px;
                margin-bottom: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            .object-list {
                margin-top: 20px;
            }
            .object-item {
                background: #f8f9fa;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 4px;
            }
            .confidence-bar {
                height: 5px;
                background: #e9ecef;
                margin-top: 5px;
                border-radius: 2px;
            }
            .confidence-fill {
                height: 100%;
                background: #28a745;
                border-radius: 2px;
            }
            .video-summary {
                margin-top: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Video Processing Assistant</h1>
            <p>Upload a video file to process it with AI Vision for object detection.</p>
            <div class="upload-form">
                <div class="file-input">
                    <input type="file" id="video" accept="video/*" />
                </div>
                <button class="button" onclick="uploadVideo()">Upload & Process Video</button>
            </div>
            <div class="progress" id="progress">
                <h3>Processing...</h3>
                <p id="status"></p>
            </div>
        </div>

        <div class="container">
            <h2>Object Search</h2>
            <div class="search-container">
                <input type="text" id="searchQuery" class="search-input" placeholder="Search for objects (e.g., 'person', 'car')">
                <button class="button" onclick="searchObjects()">Search</button>
            </div>
            <div id="searchResults" class="object-list"></div>
        </div>

        <div class="container">
            <h2>Processing Results</h2>
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

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.status === 'success') {
                    document.getElementById('status').textContent = 'Processing complete!';
                    displayResults(result);
                } else {
                    document.getElementById('status').textContent = 'Error: ' + result.message;
                }
            } catch (error) {
                document.getElementById('status').textContent = 'Error: ' + error.message;
                console.error('Error:', error);
            }
        }

        async function searchObjects() {
            const query = document.getElementById('searchQuery').value;
            if (!query) {
                alert('Please enter a search term');
                return;
            }

            try {
                const response = await fetch(`/search?query=${encodeURIComponent(query)}`);
                const results = await response.json();
                
                const resultsDiv = document.getElementById('searchResults');
                resultsDiv.innerHTML = '';
                
                results.forEach(obj => {
                    const confidence = obj.confidence * 100;
                    const item = document.createElement('div');
                    item.className = 'object-item';
                    item.innerHTML = `
                        <strong>${obj.label}</strong> (${obj.category})
                        <p>${obj.description}</p>
                        <small>Frame: ${obj.frame_number}, Confidence: ${confidence.toFixed(1)}%</small>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${confidence}%"></div>
                        </div>
                    `;
                    resultsDiv.appendChild(item);
                });
            } catch (error) {
                console.error('Error searching objects:', error);
                alert('Error searching objects');
            }
        }

        function displayResults(result) {
            const resultsDiv = document.getElementById('results');
            
            // Create video summary section
            let summaryHtml = '<div class="video-summary">';
            summaryHtml += '<h3>Video Summary</h3>';
            
            // Display object statistics
            const objectCounts = {};
            result.results.forEach(frame => {
                frame.objects.forEach(obj => {
                    objectCounts[obj.label] = (objectCounts[obj.label] || 0) + 1;
                });
            });
            
            summaryHtml += '<h4>Detected Objects:</h4><ul>';
            Object.entries(objectCounts)
                .sort((a, b) => b[1] - a[1])
                .forEach(([label, count]) => {
                    summaryHtml += `<li>${label}: ${count} occurrences</li>`;
                });
            summaryHtml += '</ul></div>';
            
            // Display frame details
            let framesHtml = '<h3>Frame Details</h3>';
            result.results.forEach(frame => {
                if (frame.objects.length > 0) {
                    framesHtml += `<div class="object-item">`;
                    framesHtml += `<strong>Frame ${frame.frame_number}</strong>`;
                    frame.objects.forEach(obj => {
                        const confidence = obj.confidence * 100;
                        framesHtml += `
                            <p>${obj.label} (${obj.category}): ${obj.description}</p>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${confidence}%"></div>
                            </div>
                        `;
                    });
                    framesHtml += '</div>';
                }
            });
            
            resultsDiv.innerHTML = summaryHtml + framesHtml;
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

        # Start video processing in storage
        await video_processor.storage.start_video(
            filename=video.filename,
            total_frames=0,  # Will be updated after loading video
            metadata={"upload_time": datetime.now().isoformat()}
        )

        results = []
        async for frame, metadata in video_processor.process_video(temp_path):
            results.append({
                "frame_number": metadata["frame_number"],
                "progress": metadata["progress_percent"],
                "frame_size": metadata["frame_size"],
                "objects": metadata["objects"]
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
        print(f"Error processing video: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.get("/search")
async def search_objects(query: str):
    """Search for objects in processed frames"""
    try:
        objects = await video_processor.search_objects(query)
        return JSONResponse(objects)
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
    uvicorn.run(app, host="127.0.0.1", port=8089)
