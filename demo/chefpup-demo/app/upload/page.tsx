"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Upload, FileVideo, FileAudio, Check, AlertCircle } from "lucide-react"

export default function UploadPage() {
  const router = useRouter()
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [audioFiles, setAudioFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string } | null>(null)

  const handleVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (file.type.startsWith("video/")) {
        setVideoFile(file)
      } else {
        alert("Please select a valid video file")
      }
    }
  }

  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      const validFiles = files.filter((file) => file.type === "audio/mpeg" || file.name.toLowerCase().endsWith(".mp3"))

      if (validFiles.length !== files.length) {
        alert("Please select only MP3 audio files")
      }

      // Only keep up to 4 files
      setAudioFiles((prev) => {
        const combined = [...prev, ...validFiles]
        return combined.slice(0, 4)
      })
    }
  }

  const removeAudioFile = (index: number) => {
    setAudioFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (!videoFile) {
      alert("Please select a video file")
      return
    }

    if (audioFiles.length !== 4) {
      alert("Please upload exactly 4 MP3 files")
      return
    }

    setUploading(true)
    setUploadStatus(null)

    try {
      // Create FormData to send files
      const formData = new FormData()
      formData.append("video", videoFile)

      audioFiles.forEach((file, index) => {
        formData.append(`audio${index + 1}`, file)
      })

      // Upload files to server
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Upload failed")
      }

      setUploadStatus({
        success: true,
        message: "Files uploaded successfully! Redirecting to player...",
      })

      // Redirect to the main page after a short delay
      setTimeout(() => {
        router.push("/")
      }, 2000)
    } catch (error) {
      console.error("Upload error:", error)
      setUploadStatus({
        success: false,
        message: "Upload failed. Please try again.",
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold mb-6 text-center">Upload Media Files</h1>

        {/* Video Upload */}
        <div className="mb-6">
          <h2 className="text-lg font-medium mb-2 flex items-center gap-2">
            <FileVideo className="w-5 h-5" />
            Video Upload
          </h2>
          <div
            className={`border-2 border-dashed rounded-lg p-4 text-center ${videoFile ? "border-green-300 bg-green-50" : "border-gray-300"}`}
          >
            {videoFile ? (
              <div className="flex items-center justify-between">
                <span className="text-sm truncate max-w-[200px]">{videoFile.name}</span>
                <button onClick={() => setVideoFile(null)} className="text-red-500 hover:text-red-700">
                  Remove
                </button>
              </div>
            ) : (
              <>
                <label className="block cursor-pointer">
                  <span className="text-sm text-gray-500">Click to select video file</span>
                  <input type="file" accept="video/*" onChange={handleVideoChange} className="hidden" />
                </label>
              </>
            )}
          </div>
        </div>

        {/* Audio Upload */}
        <div className="mb-6">
          <h2 className="text-lg font-medium mb-2 flex items-center gap-2">
            <FileAudio className="w-5 h-5" />
            Audio Files (4 MP3 files)
          </h2>
          <div
            className={`border-2 border-dashed rounded-lg p-4 ${audioFiles.length === 4 ? "border-green-300 bg-green-50" : "border-gray-300"}`}
          >
            {audioFiles.length > 0 ? (
              <div className="space-y-2">
                {audioFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between text-sm">
                    <span className="truncate max-w-[200px]">
                      {index + 1}. {file.name}
                    </span>
                    <button onClick={() => removeAudioFile(index)} className="text-red-500 hover:text-red-700">
                      Remove
                    </button>
                  </div>
                ))}
                {audioFiles.length < 4 && (
                  <label className="block cursor-pointer mt-2 text-center">
                    <span className="text-sm text-blue-500 hover:text-blue-700">
                      + Add more files ({4 - audioFiles.length} remaining)
                    </span>
                    <input
                      type="file"
                      accept="audio/mpeg,.mp3"
                      multiple
                      onChange={handleAudioChange}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            ) : (
              <label className="block cursor-pointer text-center">
                <span className="text-sm text-gray-500">Click to select MP3 files</span>
                <input type="file" accept="audio/mpeg,.mp3" multiple onChange={handleAudioChange} className="hidden" />
              </label>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Please upload exactly 4 MP3 files. They will be renamed to 1.mp3, 2.mp3, etc.
          </p>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!videoFile || audioFiles.length !== 4 || uploading}
          className={`
            w-full py-2 rounded-lg flex items-center justify-center gap-2
            ${
              !videoFile || audioFiles.length !== 4 || uploading
                ? "bg-gray-300 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600 text-white"
            }
          `}
        >
          {uploading ? (
            <>
              <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"></div>
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Upload Files
            </>
          )}
        </button>

        {/* Status Message */}
        {uploadStatus && (
          <div
            className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
              uploadStatus.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
            }`}
          >
            {uploadStatus.success ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            {uploadStatus.message}
          </div>
        )}
      </div>
    </div>
  )
}

