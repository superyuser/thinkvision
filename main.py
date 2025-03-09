import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request
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

app = FastAPI(title="Ingredient Detection Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for uploaded videos
os.makedirs("temp/uploads", exist_ok=True)
os.makedirs("temp/frames", exist_ok=True)

# Mount static directories
app.mount("/temp", StaticFiles(directory="temp"), name="temp")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create static directories if they don't exist
os.makedirs("static/frames", exist_ok=True)

video_processor = VideoProcessor(debug_mode=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ingredient Detection Assistant</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: #f5f5f5;
            }
            .app-container {
                display: flex;
                height: 100vh;
            }
            .main-panel {
                flex: 3;
                padding: 20px;
                overflow-y: auto;
            }
            .sidebar {
                flex: 1;
                background: white;
                padding: 20px;
                box-shadow: -2px 0 5px rgba(0,0,0,0.1);
                overflow-y: auto;
                min-width: 300px;
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
            .button:disabled {
                background: #cccccc;
                cursor: not-allowed;
            }
            .file-input {
                border: 2px dashed #ccc;
                padding: 20px;
                text-align: center;
                border-radius: 4px;
            }
            .ingredient-list {
                margin-top: 20px;
            }
            .ingredient-item {
                background: #f8f9fa;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 4px;
                display: flex;
                align-items: center;
            }
            .ingredient-name {
                flex-grow: 1;
                font-weight: bold;
            }
            .confidence-bar {
                height: 5px;
                width: 100px;
                background: #e9ecef;
                margin-left: 10px;
                border-radius: 2px;
            }
            .confidence-fill {
                height: 100%;
                background: #28a745;
                border-radius: 2px;
            }
            .frame-container {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 20px;
            }
            .frame-item {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                width: calc(50% - 15px);
                box-sizing: border-box;
            }
            .frame-image {
                width: 100%;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            .frame-info {
                font-size: 12px;
                color: #666;
            }
            .frame-ingredients {
                margin-top: 10px;
            }
            .frame-ingredient {
                display: inline-block;
                background: #e9ecef;
                padding: 3px 8px;
                border-radius: 12px;
                margin-right: 5px;
                margin-bottom: 5px;
                font-size: 12px;
            }
            .all-ingredients-title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }
            #uploadedVideoName {
                margin-top: 10px;
                font-weight: bold;
            }
            #videoPreview {
                max-width: 100%;
                border-radius: 8px;
                margin-top: 15px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <div class="main-panel">
                <div class="container">
                    <h1>Ingredient Detection Assistant</h1>
                    <p>Upload a cooking video to detect ingredients in each frame.</p>
                    
                    <!-- Step 1: Upload Video -->
                    <div class="upload-form">
                        <h2>Step 1: Upload Video</h2>
                        <div class="file-input">
                            <input type="file" id="video" accept="video/*" onchange="handleVideoUpload()" />
                        </div>
                        <div id="uploadedVideoName"></div>
                        <video id="videoPreview" controls></video>
                    </div>
                    
                    <!-- Step 2: Process Video -->
                    <div class="upload-form" style="margin-top: 30px;">
                        <h2>Step 2: Process Video</h2>
                        <button class="button" id="processButton" onclick="processVideo()" disabled>Process Video</button>
                        <div class="progress" id="progress">
                            <h3>Processing...</h3>
                            <p id="status"></p>
                        </div>
                    </div>
                </div>
                
                <!-- Results Section -->
                <div class="container" id="resultsContainer" style="display: none;">
                    <h2>Processed Frames</h2>
                    <div id="frameResults" class="frame-container"></div>
                </div>
            </div>
            
            <!-- Sidebar for All Ingredients -->
            <div class="sidebar">
                <div class="all-ingredients-title">All Detected Ingredients</div>
                <div id="allIngredients" class="ingredient-list"></div>
            </div>
        </div>

        <script>
        let uploadedVideoPath = null;
        
        function handleVideoUpload() {
            const fileInput = document.getElementById('video');
            const file = fileInput.files[0];
            if (!file) {
                return;
            }
            
            const formData = new FormData();
            formData.append('video', file);
            
            document.getElementById('uploadedVideoName').textContent = 'Uploading: ' + file.name;
            document.getElementById('processButton').disabled = true;
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    uploadedVideoPath = data.video_path;
                    document.getElementById('uploadedVideoName').textContent = 'Uploaded: ' + file.name;
                    document.getElementById('processButton').disabled = false;
                    
                    // Show video preview
                    const videoPreview = document.getElementById('videoPreview');
                    videoPreview.src = '/temp/uploads/' + data.filename;
                    videoPreview.style.display = 'block';
                } else {
                    document.getElementById('uploadedVideoName').textContent = 'Error: ' + data.message;
                }
            })
            .catch(error => {
                document.getElementById('uploadedVideoName').textContent = 'Error: ' + error.message;
                console.error('Error:', error);
            });
        }
        
        function processVideo() {
            if (!uploadedVideoPath) {
                alert('Please upload a video first');
                return;
            }
            
            document.getElementById('progress').style.display = 'block';
            document.getElementById('status').textContent = 'Starting video processing...';
            document.getElementById('processButton').disabled = true;
            document.getElementById('resultsContainer').style.display = 'none';
            document.getElementById('allIngredients').innerHTML = '';
            document.getElementById('frameResults').innerHTML = '';
            
            // Create FormData to send the video path
            const formData = new FormData();
            formData.append('video_path', uploadedVideoPath);
            
            fetch('/process', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById('status').textContent = 'Processing complete!';
                document.getElementById('resultsContainer').style.display = 'block';
                
                // Display all ingredients in sidebar
                displayAllIngredients(data.all_ingredients || []);
                
                // Display frame results
                displayFrameResults(data.frames || []);
                
                document.getElementById('processButton').disabled = false;
            })
            .catch(error => {
                document.getElementById('status').textContent = 'Error: ' + error;
                document.getElementById('processButton').disabled = false;
                console.error('Error:', error);
            });
        }
        
        function displayAllIngredients(ingredients) {
            const container = document.getElementById('allIngredients');
            container.innerHTML = '';
            
            if (!ingredients || ingredients.length === 0) {
                container.innerHTML = '<p>No ingredients detected</p>';
                return;
            }
            
            // Sort ingredients alphabetically
            ingredients.sort();
            
            ingredients.forEach(ingredient => {
                const item = document.createElement('div');
                item.className = 'ingredient-item';
                item.innerHTML = `
                    <div class="ingredient-name">${ingredient}</div>
                `;
                container.appendChild(item);
            });
        }
        
        function displayFrameResults(frames) {
            const container = document.getElementById('frameResults');
            container.innerHTML = '';
            
            if (!frames || frames.length === 0) {
                container.innerHTML = '<p>No frames processed</p>';
                return;
            }
            
            frames.forEach(frame => {
                const frameItem = document.createElement('div');
                frameItem.className = 'frame-item';
                
                // Create ingredients list for this frame
                let ingredientsHtml = '';
                if (frame.ingredients && frame.ingredients.length > 0) {
                    frame.ingredients.forEach(ingredient => {
                        ingredientsHtml += `<span class="frame-ingredient">${ingredient.label}</span>`;
                    });
                } else {
                    ingredientsHtml = '<p>No ingredients detected in this frame</p>';
                }
                
                frameItem.innerHTML = `
                    <img src="${frame.frame_path}" class="frame-image" alt="Frame">
                    <div class="frame-ingredients">
                        ${ingredientsHtml}
                    </div>
                `;
                container.appendChild(frameItem);
            });
        }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_video(video: UploadFile = File(...)):
    """Handle video file upload"""
    try:
        # Create a unique filename
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"
        file_path = os.path.join("temp", "uploads", filename)
        
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await video.read()
            await out_file.write(content)
        
        return JSONResponse({
            "status": "success",
            "message": "Video uploaded successfully",
            "video_path": file_path,
            "filename": filename
        })
        
    except Exception as e:
        print(f"Error uploading video: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post("/process")
async def process_video(request: Request):
    """Process uploaded video to detect ingredients"""
    form = await request.form()
    video_path = form.get("video_path")
    
    if not video_path:
        return {"error": "No video path provided"}
    
    if not os.path.exists(video_path):
        return {"error": f"Video file not found at {video_path}"}
    
    # Create a VideoProcessor instance
    processor = VideoProcessor()
    
    # Create a list to store all unique ingredients
    all_ingredients = set()
    
    # Create a list to store processed frames
    processed_frames = []
    
    # Process the video
    try:
        print(f"Processing video: {video_path}")
        async for result in processor.process_video(video_path, sample_rate=10):
            frame_path = result.get("frame_path", "")
            ingredients = result.get("ingredients", [])
            
            # Debug information
            print(f"Frame: {frame_path}")
            print(f"Detected {len(ingredients)} ingredients in this frame")
            
            for ingredient in ingredients:
                print(f"  - {ingredient['label']} (confidence: {ingredient['confidence']:.2f})")
                all_ingredients.add(ingredient['label'])
            
            processed_frames.append({
                "frame_path": frame_path,
                "ingredients": ingredients
            })
        
        # Return the processed frames and all unique ingredients
        return {
            "status": "success",
            "message": "Video processed successfully",
            "all_ingredients": list(all_ingredients),
            "frames": processed_frames
        }
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error processing video: {str(e)}"}

@app.get("/status")
async def get_status():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8089)
