import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, WebSocket, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from pathlib import Path
import tempfile
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aiofiles
from typing import Dict, List, Any
import time

# Load environment variables with absolute path
env_path = Path(__file__).resolve().parent.parent / '.env'
print(f"Looking for .env at: {env_path}")
print(f"File exists: {env_path.exists()}")

if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")

load_dotenv(env_path)

# Verify Google API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
print("Successfully loaded GOOGLE_API_KEY")

# Initialize FastAPI app
app = FastAPI(title="ThinkVision", description="Video ingredient detection with Gemini Vision")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory if it doesn't exist
temp_dir = Path("temp")
temp_dir.mkdir(exist_ok=True)

# Create frames directory if it doesn't exist
frames_dir = Path("frames")
frames_dir.mkdir(exist_ok=True)

# Global variables
video_processor = None
current_video_path = None
processing_complete = False
debug_mode = False  # Default debug mode to False for better performance

@app.get("/", response_class=HTMLResponse)
async def root():
    """Return HTML page for video processing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ThinkVision - Video Ingredient Detection</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .upload-section {
                margin: 20px 0;
                padding: 20px;
                border: 1px dashed #ccc;
                border-radius: 8px;
                text-align: center;
            }
            .results-section {
                display: flex;
                flex-wrap: wrap;
                margin-top: 20px;
            }
            .video-container {
                flex: 1;
                min-width: 300px;
                margin-right: 20px;
            }
            .ingredients-container {
                flex: 1;
                min-width: 300px;
            }
            .frames-container {
                margin-top: 20px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .frame-item {
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 4px;
                width: 200px;
                cursor: pointer;
            }
            .frame-item img {
                width: 100%;
                height: auto;
            }
            .frame-item.selected {
                border-color: #007bff;
                background-color: #f0f7ff;
            }
            .ingredient-list {
                list-style-type: none;
                padding: 0;
            }
            .ingredient-list li {
                padding: 8px 12px;
                margin-bottom: 5px;
                background-color: #f1f1f1;
                border-radius: 4px;
            }
            .frame-ingredients {
                margin-top: 5px;
                font-size: 0.9em;
            }
            .frame-ingredients span {
                display: inline-block;
                background-color: #e9f5e9;
                padding: 2px 6px;
                margin: 2px;
                border-radius: 3px;
                font-size: 0.8em;
            }
            .loading {
                text-align: center;
                margin: 20px 0;
            }
            .debug-section {
                margin-top: 20px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
            .debug-response {
                white-space: pre-wrap;
                font-family: monospace;
                font-size: 0.9em;
                background-color: #f1f1f1;
                padding: 10px;
                border-radius: 4px;
                max-height: 300px;
                overflow-y: auto;
            }
            .debug-toggle {
                margin: 10px 0;
                display: flex;
                align-items: center;
            }
            .debug-toggle input {
                margin-right: 10px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            input[type="file"] {
                margin: 10px 0;
            }
            .status {
                margin: 10px 0;
                padding: 10px;
                border-radius: 4px;
            }
            .status.success {
                background-color: #d4edda;
                color: #155724;
            }
            .status.error {
                background-color: #f8d7da;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ThinkVision - Video Ingredient Detection</h1>
            
            <div class="upload-section">
                <h2>Upload Cooking Video</h2>
                <form id="upload-form" enctype="multipart/form-data">
                    <input type="file" id="video-file" name="video" accept="video/*" required>
                    <div class="debug-toggle">
                        <input type="checkbox" id="debug-mode" name="debug-mode">
                        <label for="debug-mode">Enable Debug Mode (slower but provides detailed information)</label>
                    </div>
                    <button type="submit">Upload & Process</button>
                </form>
                <div id="upload-status" class="status"></div>
            </div>
            
            <div class="results-section" style="display: none;" id="results-container">
                <div class="video-container">
                    <h2>Video</h2>
                    <video id="video-player" controls style="width: 100%; max-height: 400px;"></video>
                </div>
                
                <div class="ingredients-container">
                    <h2>Detected Ingredients</h2>
                    <ul id="ingredient-list" class="ingredient-list"></ul>
                </div>
            </div>
            
            <div id="frames-section" style="display: none;">
                <h2>Processed Frames</h2>
                <div id="frames-container" class="frames-container"></div>
            </div>
            
            <div id="debug-section" class="debug-section" style="display: none;">
                <h2>Debug Information</h2>
                <h3>Raw Gemini Vision Response</h3>
                <div id="debug-response" class="debug-response"></div>
            </div>
            
            <div id="loading" class="loading" style="display: none;">
                <h2>Processing Video...</h2>
                <p>This may take a few minutes depending on the video length.</p>
            </div>
        </div>
        
        <script>
            let socket;
            let selectedFrame = null;
            
            document.getElementById('upload-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData();
                const videoFile = document.getElementById('video-file').files[0];
                const debugMode = document.getElementById('debug-mode').checked;
                
                if (!videoFile) {
                    showStatus('Please select a video file', 'error');
                    return;
                }
                
                formData.append('video', videoFile);
                
                // Show loading state
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results-container').style.display = 'none';
                document.getElementById('frames-section').style.display = 'none';
                document.getElementById('debug-section').style.display = 'none';
                
                try {
                    // Upload the video
                    const uploadResponse = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!uploadResponse.ok) {
                        throw new Error('Video upload failed');
                    }
                    
                    const uploadResult = await uploadResponse.json();
                    showStatus('Video uploaded successfully. Starting processing...', 'success');
                    
                    // Start processing with debug mode parameter
                    const processResponse = await fetch('/process?debug_mode=' + debugMode, {
                        method: 'POST'
                    });
                    
                    if (!processResponse.ok) {
                        throw new Error('Failed to start video processing');
                    }
                    
                    // Connect to WebSocket for real-time updates
                    connectWebSocket();
                    
                } catch (error) {
                    console.error('Error:', error);
                    showStatus('Error: ' + error.message, 'error');
                    document.getElementById('loading').style.display = 'none';
                }
            });
            
            function connectWebSocket() {
                // Close existing socket if any
                if (socket) {
                    socket.close();
                }
                
                // Create new WebSocket connection
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                socket = new WebSocket(wsUrl);
                
                socket.onopen = function(e) {
                    console.log('WebSocket connection established');
                };
                
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    if (data.status === 'processing') {
                        // Update progress
                        showStatus(`Processing: Frame ${data.frame_number}`, 'success');
                        
                    } else if (data.status === 'complete') {
                        // Processing complete, show results
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('results-container').style.display = 'flex';
                        document.getElementById('frames-section').style.display = 'block';
                        
                        // Set video source
                        const videoPlayer = document.getElementById('video-player');
                        videoPlayer.src = data.video_url;
                        
                        // Display ingredients
                        displayIngredients(data.ingredients);
                        
                        // Display processed frames
                        displayFrames(data.frames);
                        
                        showStatus('Video processing complete!', 'success');
                    }
                };
                
                socket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    showStatus('Error in WebSocket connection', 'error');
                };
                
                socket.onclose = function(event) {
                    console.log('WebSocket connection closed');
                };
            }
            
            function displayIngredients(ingredients) {
                const ingredientList = document.getElementById('ingredient-list');
                ingredientList.innerHTML = '';
                
                if (ingredients && ingredients.length > 0) {
                    ingredients.forEach(ingredient => {
                        const li = document.createElement('li');
                        li.textContent = ingredient;
                        ingredientList.appendChild(li);
                    });
                } else {
                    const li = document.createElement('li');
                    li.textContent = 'No ingredients detected';
                    ingredientList.appendChild(li);
                }
            }
            
            function displayFrames(frames) {
                const framesContainer = document.getElementById('frames-container');
                framesContainer.innerHTML = '';
                
                if (frames && frames.length > 0) {
                    frames.forEach(frame => {
                        const frameItem = document.createElement('div');
                        frameItem.className = 'frame-item';
                        frameItem.dataset.frameNumber = frame.frame_number;
                        
                        const img = document.createElement('img');
                        img.src = frame.frame_url;
                        img.alt = `Frame ${frame.frame_number}`;
                        
                        const info = document.createElement('div');
                        info.innerHTML = `<strong>Frame ${frame.frame_number}</strong><br>Time: ${frame.timestamp.toFixed(2)}s`;
                        
                        const ingredients = document.createElement('div');
                        ingredients.className = 'frame-ingredients';
                        
                        // Add ingredients for this frame
                        const frameIngredients = frame.objects
                            .filter(obj => obj.category !== 'debug' && obj.confidence >= 0.1)
                            .map(obj => obj.label);
                            
                        if (frameIngredients.length > 0) {
                            frameIngredients.forEach(ingredient => {
                                const span = document.createElement('span');
                                span.textContent = ingredient;
                                ingredients.appendChild(span);
                            });
                        } else {
                            const span = document.createElement('span');
                            span.textContent = 'No ingredients';
                            ingredients.appendChild(span);
                        }
                        
                        frameItem.appendChild(img);
                        frameItem.appendChild(info);
                        frameItem.appendChild(ingredients);
                        
                        // Add click event to show debug info
                        frameItem.addEventListener('click', () => {
                            // Deselect previously selected frame
                            if (selectedFrame) {
                                selectedFrame.classList.remove('selected');
                            }
                            
                            // Select this frame
                            frameItem.classList.add('selected');
                            selectedFrame = frameItem;
                            
                            // Show debug info if available
                            const debugObj = frame.objects.find(obj => obj.category === 'debug');
                            const debugSection = document.getElementById('debug-section');
                            const debugResponse = document.getElementById('debug-response');
                            
                            if (debugObj && debugObj.raw_response) {
                                debugSection.style.display = 'block';
                                debugResponse.textContent = debugObj.raw_response;
                            } else {
                                // Check if any object has raw_response
                                const anyDebugInfo = frame.objects.find(obj => obj.raw_response);
                                
                                if (anyDebugInfo && anyDebugInfo.raw_response) {
                                    debugSection.style.display = 'block';
                                    debugResponse.textContent = anyDebugInfo.raw_response;
                                } else {
                                    debugSection.style.display = 'none';
                                }
                            }
                        });
                        
                        framesContainer.appendChild(frameItem);
                    });
                } else {
                    framesContainer.innerHTML = '<p>No frames processed</p>';
                }
            }
            
            function showStatus(message, type) {
                const statusElement = document.getElementById('upload-status');
                statusElement.textContent = message;
                statusElement.className = 'status ' + type;
            }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_video(video: UploadFile = File(...)):
    """Handle video file upload"""
    global current_video_path
    
    try:
        # Create temp directory if it doesn't exist
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        filename = f"{int(time.time())}_{video.filename}"
        file_path = temp_dir / filename
        
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await video.read()
            await out_file.write(content)
        
        # Store path for processing
        current_video_path = str(file_path)
        
        # Create video URL for frontend
        video_url = f"/temp/{filename}"
        
        return JSONResponse({
            "status": "success",
            "message": "Video uploaded successfully",
            "video_url": video_url,
            "file_path": str(file_path)
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.post("/process")
async def process_video(background_tasks: BackgroundTasks, debug_mode: bool = False):
    """Start video processing in background"""
    global video_processor, current_video_path, processing_complete
    
    if not current_video_path or not Path(current_video_path).exists():
        return JSONResponse({
            "status": "error",
            "message": "No video uploaded or video file not found"
        }, status_code=400)
    
    # Reset processing state
    processing_complete = False
    
    # Initialize video processor with debug mode setting
    video_processor = VideoProcessor(debug_mode=debug_mode)
    
    # Start processing in background
    background_tasks.add_task(process_video_task)
    
    return {"status": "processing", "message": "Video processing started"}

async def process_video_task():
    """Process video and store results"""
    global video_processor, current_video_path, processing_complete
    
    try:
        # Load video
        if not await video_processor.load_video(current_video_path):
            return
        
        # Process video with sample rate of 10 frames
        async for update in video_processor.process_video(sample_rate=10):
            # Send update to all active connections
            for connection in active_connections:
                await connection.send_json({
                    "status": "processing",
                    **update
                })
        
        # Get final results
        results = {
            "status": "complete",
            "processed_frames": len(video_processor.frame_ingredients),
            "total_frames": video_processor.frame_count,
            "all_ingredients": list(video_processor.all_ingredients),
            "frame_ingredients": video_processor.frame_ingredients
        }
        
        # Store results
        processing_complete = True
        
        # Send final results to all active connections
        for connection in active_connections:
            await connection.send_json(results)
        
    except Exception as e:
        # Send error to all active connections
        for connection in active_connections:
            await connection.send_json({
                "status": "error",
                "message": str(e)
            })
    finally:
        # Close video
        video_processor.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time processing updates"""
    await websocket.accept()
    
    # Add to active connections
    active_connections.add(websocket)
    
    try:
        # Send current results if available
        if processing_complete:
            await websocket.send_json({
                "status": "complete",
                "processed_frames": len(video_processor.frame_ingredients),
                "total_frames": video_processor.frame_count,
                "all_ingredients": list(video_processor.all_ingredients),
                "frame_ingredients": video_processor.frame_ingredients
            })
        
        # Keep connection open
        while True:
            await websocket.receive_text()
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove from active connections
        active_connections.remove(websocket)

@app.get("/status")
async def get_status():
    """Health check endpoint"""
    return {"status": "running"}

def start_server():
    """Start the FastAPI server"""
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 9000))  # Using port 9000 instead
    uvicorn.run("src.main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    start_server()
