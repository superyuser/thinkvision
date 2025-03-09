import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.video_processor import VideoProcessor
import tempfile
import aiofiles
from pathlib import Path
from datetime import datetime
import time
import json

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

# Create static directories if they don't exist
os.makedirs("static/frames", exist_ok=True)
os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Mount static directories
app.mount("/temp", StaticFiles(directory="temp"), name="temp")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

video_processor = VideoProcessor(debug_mode=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ingredient Detection Assistant</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                display: flex;
                min-height: 100vh;
            }
            .sidebar {
                width: 300px;
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            }
            .main-content {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }
            h1 {
                color: #ecf0f1;
                font-size: 24px;
                margin-bottom: 20px;
            }
            h2 {
                color: #ecf0f1;
                font-size: 18px;
                margin-top: 30px;
                border-bottom: 1px solid #34495e;
                padding-bottom: 10px;
            }
            .step-container {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .step-title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #2c3e50;
            }
            .btn {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.3s;
            }
            .btn:hover {
                background-color: #2980b9;
            }
            .btn:disabled {
                background-color: #95a5a6;
                cursor: not-allowed;
            }
            .file-input {
                margin-bottom: 15px;
            }
            .progress-container {
                margin-top: 15px;
                display: none;
            }
            .progress-bar {
                height: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-top: 5px;
                overflow: hidden;
            }
            .progress {
                height: 100%;
                background-color: #2ecc71;
                width: 0%;
                transition: width 0.3s;
            }
            .ingredient-list {
                list-style-type: none;
                padding: 0;
                margin: 0;
            }
            .ingredient-item {
                padding: 8px 0;
                border-bottom: 1px solid #34495e;
                display: flex;
                align-items: center;
            }
            .confidence-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 10px;
            }
            .high-confidence {
                background-color: #2ecc71;
            }
            .medium-confidence {
                background-color: #f39c12;
            }
            .low-confidence {
                background-color: #e74c3c;
            }
            .frame-container {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }
            .frame-card {
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                width: calc(50% - 10px);
                margin-bottom: 20px;
            }
            .frame-image {
                width: 100%;
                height: 300px;
                object-fit: cover;
            }
            .frame-details {
                padding: 15px;
            }
            .frame-ingredients {
                list-style-type: none;
                padding: 0;
                margin: 10px 0 0 0;
            }
            .frame-ingredient-item {
                padding: 5px 0;
                border-bottom: 1px solid #ecf0f1;
                font-size: 14px;
            }
            .error-message {
                color: #e74c3c;
                background-color: #fadbd8;
                padding: 10px;
                border-radius: 4px;
                margin-top: 10px;
                display: none;
            }
            .video-preview {
                max-width: 100%;
                max-height: 300px;
                margin-top: 15px;
                display: none;
            }
            .json-info {
                background-color: #e8f4f8;
                padding: 15px;
                border-radius: 4px;
                margin-top: 15px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="sidebar">
                <h1>Ingredient Detection Assistant</h1>
                
                <h2>Detected Ingredients</h2>
                <div id="ingredientsList">
                    <p>No ingredients detected yet. Upload and process a video to see ingredients.</p>
                </div>
            </div>
            
            <div class="main-content">
                <div class="step-container">
                    <div class="step-title">Step 1: Upload Video</div>
                    <input type="file" id="videoFile" class="file-input" accept="video/*">
                    <button id="uploadBtn" class="btn">Upload Video</button>
                    <div id="uploadError" class="error-message"></div>
                    <video id="videoPreview" class="video-preview" controls></video>
                </div>
                
                <div class="step-container">
                    <div class="step-title">Step 2: Process Video</div>
                    <button id="processBtn" class="btn" disabled>Process Video</button>
                    <div id="processError" class="error-message"></div>
                    <div id="progressContainer" class="progress-container">
                        <div>Processing video... <span id="progressText">0%</span></div>
                        <div class="progress-bar">
                            <div id="progressBar" class="progress"></div>
                        </div>
                    </div>
                    <div id="jsonInfo" class="json-info">
                        <div id="jsonPath"></div>
                    </div>
                </div>
                
                <div class="step-container">
                    <div class="step-title">Step 3: Results</div>
                    <div id="framesContainer" class="frame-container">
                        <p>Process a video to see results.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Global variables
            let uploadedVideoPath = '';
            let jsonFilePath = '';
            
            // DOM elements
            const videoFileInput = document.getElementById('videoFile');
            const uploadBtn = document.getElementById('uploadBtn');
            const processBtn = document.getElementById('processBtn');
            const videoPreview = document.getElementById('videoPreview');
            const uploadError = document.getElementById('uploadError');
            const processError = document.getElementById('processError');
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const ingredientsList = document.getElementById('ingredientsList');
            const framesContainer = document.getElementById('framesContainer');
            const jsonInfo = document.getElementById('jsonInfo');
            const jsonPath = document.getElementById('jsonPath');
            
            // Event listeners
            uploadBtn.addEventListener('click', uploadVideo);
            processBtn.addEventListener('click', processVideo);
            
            // Functions
            function uploadVideo() {
                const file = videoFileInput.files[0];
                if (!file) {
                    showError(uploadError, 'Please select a video file first.');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                // Reset UI
                uploadError.style.display = 'none';
                uploadBtn.disabled = true;
                uploadBtn.textContent = 'Uploading...';
                
                // Upload video
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    // Update UI
                    uploadBtn.textContent = 'Upload Complete';
                    uploadedVideoPath = data.file_path;
                    
                    // Show video preview
                    videoPreview.src = `/temp/${data.filename}`;
                    videoPreview.style.display = 'block';
                    
                    // Enable process button
                    processBtn.disabled = false;
                })
                .catch(error => {
                    showError(uploadError, `Error uploading video: ${error.message}`);
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload Video';
                });
            }
            
            function processVideo() {
                if (!uploadedVideoPath) {
                    showError(processError, 'Please upload a video first.');
                    return;
                }
                
                // Reset UI
                processError.style.display = 'none';
                processBtn.disabled = true;
                processBtn.textContent = 'Processing...';
                progressContainer.style.display = 'block';
                progressBar.style.width = '0%';
                progressText.textContent = '0%';
                framesContainer.innerHTML = '<p>Processing video...</p>';
                ingredientsList.innerHTML = '<p>Detecting ingredients...</p>';
                jsonInfo.style.display = 'none';
                
                // Create form data
                const formData = new FormData();
                formData.append('video_path', uploadedVideoPath);
                
                // Process video
                fetch('/process', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    // Update UI
                    processBtn.textContent = 'Processing Complete';
                    progressBar.style.width = '100%';
                    progressText.textContent = '100%';
                    
                    // Display frames
                    displayFrames(data.frames);
                    
                    // Display ingredients
                    displayIngredients(data.unique_ingredients);
                    
                    // Display JSON file info
                    if (data.json_file) {
                        jsonFilePath = data.json_file;
                        jsonInfo.style.display = 'block';
                        jsonPath.textContent = `JSON file saved to: ${data.json_file}`;
                    }
                })
                .catch(error => {
                    showError(processError, `Error processing video: ${error.message}`);
                    processBtn.disabled = false;
                    processBtn.textContent = 'Process Video';
                    progressContainer.style.display = 'none';
                });
            }
            
            function displayFrames(frames) {
                if (!frames || frames.length === 0) {
                    framesContainer.innerHTML = '<p>No frames were processed.</p>';
                    return;
                }
                
                framesContainer.innerHTML = '';
                
                frames.forEach(frame => {
                    const frameCard = document.createElement('div');
                    frameCard.className = 'frame-card';
                    
                    const frameImage = document.createElement('img');
                    frameImage.className = 'frame-image';
                    frameImage.src = frame.frame;
                    frameImage.alt = 'Processed Frame';
                    
                    const frameDetails = document.createElement('div');
                    frameDetails.className = 'frame-details';
                    
                    const ingredientsTitle = document.createElement('div');
                    ingredientsTitle.className = 'step-title';
                    ingredientsTitle.textContent = `Ingredients (${frame.ingredients.length})`;
                    
                    const ingredientsList = document.createElement('ul');
                    ingredientsList.className = 'frame-ingredients';
                    
                    frame.ingredients.forEach(ingredient => {
                        const ingredientItem = document.createElement('li');
                        ingredientItem.className = 'frame-ingredient-item';
                        
                        // Determine confidence class
                        let confidenceClass = 'low-confidence';
                        if (ingredient.confidence >= 0.8) {
                            confidenceClass = 'high-confidence';
                        } else if (ingredient.confidence >= 0.5) {
                            confidenceClass = 'medium-confidence';
                        }
                        
                        ingredientItem.innerHTML = `
                            <span class="confidence-indicator ${confidenceClass}"></span>
                            ${ingredient.label} (${(ingredient.confidence * 100).toFixed(0)}%)
                        `;
                        
                        ingredientsList.appendChild(ingredientItem);
                    });
                    
                    frameDetails.appendChild(ingredientsTitle);
                    frameDetails.appendChild(ingredientsList);
                    
                    frameCard.appendChild(frameImage);
                    frameCard.appendChild(frameDetails);
                    
                    framesContainer.appendChild(frameCard);
                });
            }
            
            function displayIngredients(ingredients) {
                if (!ingredients || ingredients.length === 0) {
                    ingredientsList.innerHTML = '<p>No ingredients detected.</p>';
                    return;
                }
                
                const list = document.createElement('ul');
                list.className = 'ingredient-list';
                
                ingredients.forEach(ingredient => {
                    const item = document.createElement('li');
                    item.className = 'ingredient-item';
                    item.textContent = ingredient;
                    list.appendChild(item);
                });
                
                ingredientsList.innerHTML = '';
                ingredientsList.appendChild(list);
            }
            
            function showError(element, message) {
                element.textContent = message;
                element.style.display = 'block';
                setTimeout(() => {
                    element.style.display = 'none';
                }, 5000);
            }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and save it to the temp directory"""
    try:
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = f"temp/{filename}"
        
        # Save the uploaded file
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        return JSONResponse({
            "status": "success",
            "message": "Video uploaded successfully",
            "file_path": file_path,
            "filename": filename
        })
        
    except Exception as e:
        print(f"Error uploading video: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Failed to upload video: {str(e)}"
        }, status_code=500)

@app.post("/process")
async def process_video(video_path: str = Form(...)):
    """Process a video file and extract ingredients from frames"""
    try:
        if not os.path.exists(video_path):
            return JSONResponse(
                status_code=404,
                content={"error": f"Video file not found: {video_path}"}
            )
            
        # Process video with VideoProcessor
        frames = []
        unique_ingredients = []
        
        async for result in video_processor.process_video(video_path):
            if "summary" in result:
                # This is the final summary result
                unique_ingredients = result.get("unique_ingredients", [])
                
                # Save ingredients to JSON file
                ingredients_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "video_path": video_path,
                    "ingredients": unique_ingredients
                }
                
                # Create output directory if it doesn't exist
                os.makedirs("output", exist_ok=True)
                
                # Generate a filename based on timestamp
                json_filename = f"output/ingredients_{time.strftime('%Y%m%d_%H%M%S')}.json"
                
                # Write to JSON file
                with open(json_filename, "w") as f:
                    json.dump(ingredients_data, f, indent=4)
                
                print(f"Ingredients saved to {json_filename}")
                
                # Add the JSON file path to the result
                result["json_file"] = json_filename
            else:
                # This is a frame result
                frames.append(result)
        
        return {"frames": frames, "unique_ingredients": unique_ingredients, "json_file": json_filename if 'json_filename' in locals() else None}
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process video: {str(e)}"}
        )

@app.get("/status")
async def get_status():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8089)
