"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Upload, Camera, Mic, MicOff, X } from "lucide-react"

type AppState = "initial" | "playing-user-video" | "playing-loop" | "recording" | "playing-audio"

// Direct URLs to the audio files
const AUDIO_FILES = [
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/1-H1bG7vuntLzWs3uSM72y6TlM3n76fA.MP3", // 1.MP3
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/2-YN7jtJ4pjxhnniWnkTGaVvxtlrHsfk.MP3", // 2.MP3
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/3-K5r4z7JliEYK83lzG6GDGANCJzyoyG.MP3", // 3.MP3
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/4-kHq0FaIreXwkFknbAExEy1ELiJt141.MP3", // 4.MP3
]

export default function Home() {
  const [appState, setAppState] = useState<AppState>("initial")
  const [userVideoSrc, setUserVideoSrc] = useState<string | null>(null)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [currentAudioIndex, setCurrentAudioIndex] = useState(0) // Changed to 0-based index
  const [videoPlaying, setVideoPlaying] = useState(true)
  const [videoReady, setVideoReady] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const backgroundVideoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const playAttemptTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Safe play function with retry logic
  const safePlayVideo = (videoElement: HTMLVideoElement) => {
    if (!videoElement) return

    // Clear any existing timeout
    if (playAttemptTimeoutRef.current) {
      clearTimeout(playAttemptTimeoutRef.current)
      playAttemptTimeoutRef.current = null
    }

    // Only attempt to play if the video is ready
    if (videoElement.readyState >= 2) {
      // HAVE_CURRENT_DATA or higher
      videoElement
        .play()
        .then(() => {
          setVideoPlaying(true)
        })
        .catch(() => {
          // If the video failed to play, try again after a short delay
          playAttemptTimeoutRef.current = setTimeout(() => {
            safePlayVideo(videoElement)
          }, 1000)
        })
    } else {
      // If video is not ready, wait for the canplay event
      const canPlayHandler = () => {
        videoElement
          .play()
          .then(() => {
            setVideoPlaying(true)
          })
          .catch(() => {
            // Silent catch
          })
        videoElement.removeEventListener("canplay", canPlayHandler)
      }

      videoElement.addEventListener("canplay", canPlayHandler)
    }
  }

  // Handle video ready state
  const handleVideoCanPlay = () => {
    setVideoReady(true)
  }

  // Ensure video keeps playing
  useEffect(() => {
    if (
      videoRef.current &&
      videoReady &&
      (appState === "playing-loop" || appState === "recording" || appState === "playing-audio")
    ) {
      if (!videoPlaying && videoRef.current.paused) {
        safePlayVideo(videoRef.current)
      }
    }
  }, [appState, videoPlaying, videoReady])

  // Clean up timeouts on unmount
  useEffect(() => {
    return () => {
      if (playAttemptTimeoutRef.current) {
        clearTimeout(playAttemptTimeoutRef.current)
      }
    }
  }, [])

  // Handle file upload
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Reset video ready state for the new video
      setVideoReady(false)

      const url = URL.createObjectURL(file)
      setUserVideoSrc(url)
      setAppState("playing-user-video")
      // Don't set videoPlaying here, wait for canplay event
    }
  }

  // Handle camera access
  const handleOpenCamera = async () => {
    try {
      // Reset video ready state for the camera stream
      setVideoReady(false)

      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      setCameraStream(stream)

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        // Let the canplay event trigger the play
        setAppState("playing-user-video")
      }
    } catch (error) {
      // Silent catch
      setAppState("initial")
    }
  }

  // Handle user video ended
  const handleUserVideoEnded = () => {
    // Clean up camera stream if it exists
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop())
      setCameraStream(null)
    }

    // Reset video ready state for the looping video
    setVideoReady(false)

    // Switch to looping video
    if (videoRef.current) {
      videoRef.current.srcObject = null
      videoRef.current.src =
        "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/dog-iG92qFENAGzxJmjSaLXO210LFKJorR.mp4" // Use the new looping video URL directly
      videoRef.current.loop = true
      // Let the canplay event trigger the play
      setAppState("playing-loop")
    }
  }

  // Toggle recording
  const toggleRecording = () => {
    if (appState === "playing-audio") return // Prevent toggling while audio is playing

    // Ensure video is playing if it's ready
    if (videoRef.current && videoReady && videoRef.current.paused) {
      safePlayVideo(videoRef.current)
    }

    if (isRecording) {
      // Stop recording and play the next audio file
      setIsRecording(false)
      playNextAudio()
    } else {
      // Start recording
      setIsRecording(true)
      setAppState("recording")
    }
  }

  // Play next audio file
  const playNextAudio = () => {
    if (currentAudioIndex < AUDIO_FILES.length) {
      setAppState("playing-audio")

      // Ensure video keeps playing during audio playback if it's ready
      if (videoRef.current && videoReady && videoRef.current.paused) {
        safePlayVideo(videoRef.current)
      }

      if (audioRef.current) {
        audioRef.current.src = AUDIO_FILES[currentAudioIndex]
        audioRef.current.play().catch(() => {
          // Silent catch
          setAppState("playing-loop")
        })
      }
    }
  }

  // Handle audio ended
  const handleAudioEnded = () => {
    setAppState("playing-loop")
    setCurrentAudioIndex((prev) => Math.min(prev + 1, AUDIO_FILES.length))

    // Ensure video is playing after audio ends if it's ready
    if (videoRef.current && videoReady && videoRef.current.paused) {
      safePlayVideo(videoRef.current)
    }
  }

  // Handle video play/pause events
  const handleVideoPlay = () => {
    setVideoPlaying(true)
  }

  const handleVideoPause = () => {
    setVideoPlaying(false)
  }

  // End conversation
  const endConversation = () => {
    // Clean up resources
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop())
    }

    if (userVideoSrc) {
      URL.revokeObjectURL(userVideoSrc)
    }

    // Reset state
    setAppState("initial")
    setUserVideoSrc(null)
    setCameraStream(null)
    setIsRecording(false)
    setCurrentAudioIndex(0)
    setVideoPlaying(false)
    setVideoReady(false)
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-black">
      {appState === "initial" ? (
        <>
          {/* Background video for initial state */}
          <video
            ref={backgroundVideoRef}
            className="absolute inset-0 w-full h-full object-cover opacity-85"
            src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/dog-iG92qFENAGzxJmjSaLXO210LFKJorR.mp4" // Use the new looping video URL directly
            autoPlay
            loop
            muted
            style={{ opacity: 0.85 }}
            onCanPlay={() => {
              if (backgroundVideoRef.current) {
                backgroundVideoRef.current.play().catch(() => {
                  // Silent catch
                })
              }
            }}
          />
          <div className="absolute inset-0 flex flex-col items-end justify-end pb-20 px-10 z-10">
            <h1 className="text-3xl font-bold text-white mb-8 drop-shadow-lg text-center w-full">Meet Chefpup!</h1>

            <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center justify-center gap-2 px-6 py-4 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors shadow-lg"
              >
                <Upload className="w-5 h-5" />
                Upload Video
              </button>

              <input type="file" ref={fileInputRef} accept="video/*" onChange={handleFileUpload} className="hidden" />

              <button
                onClick={handleOpenCamera}
                className="flex items-center justify-center gap-2 px-6 py-4 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors shadow-lg"
              >
                <Camera className="w-5 h-5" />
                Open Camera
              </button>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Video player */}
          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover"
            src={userVideoSrc || undefined}
            autoPlay
            muted={appState === "playing-user-video"}
            onEnded={handleUserVideoEnded}
            onPlay={handleVideoPlay}
            onPause={handleVideoPause}
            onCanPlay={handleVideoCanPlay}
          />

          {/* Audio player (hidden) */}
          <audio ref={audioRef} onEnded={handleAudioEnded} className="hidden" />

          {/* Recording indicator */}
          {isRecording && (
            <div className="absolute top-10 right-10 flex items-center gap-2 bg-red-500 text-white px-4 py-2 rounded-full animate-pulse">
              <div className="w-3 h-3 bg-white rounded-full"></div>
              Recording...
            </div>
          )}

          {/* Audio playback indicator */}
          {appState === "playing-audio" && (
            <div className="absolute top-10 left-10 bg-blue-500 text-white px-4 py-2 rounded-full">
              Playing Audio {currentAudioIndex + 1}/4...
            </div>
          )}

          {/* Video loading indicator */}
          {!videoReady && appState !== "initial" && (
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black bg-opacity-75 text-white p-6 rounded-lg text-center">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-4 border-t-transparent border-white rounded-full animate-spin"></div>
                <p>Loading video...</p>
              </div>
            </div>
          )}

          {/* Speak button */}
          {(appState === "playing-user-video" ||
            appState === "playing-loop" ||
            appState === "recording" ||
            appState === "playing-audio") && (
            <div className="absolute bottom-10 left-1/2 transform -translate-x-1/2">
              <button
                onClick={toggleRecording}
                disabled={appState === "playing-audio" || !videoReady}
                className={`
                  flex items-center justify-center gap-2 px-6 py-3 rounded-full text-white font-medium
                  ${isRecording ? "bg-red-500 hover:bg-red-600" : "bg-blue-500 hover:bg-blue-600"}
                  ${appState === "playing-audio" || !videoReady ? "opacity-50 cursor-not-allowed" : "opacity-100"}
                  transition-all duration-200
                `}
              >
                {isRecording ? (
                  <>
                    <MicOff className="w-5 h-5" />
                    Stop
                  </>
                ) : (
                  <>
                    <Mic className="w-5 h-5" />
                    Speak
                  </>
                )}
              </button>
            </div>
          )}

          {/* End conversation button */}
          {appState !== "initial" && (
            <button
              onClick={endConversation}
              className="absolute top-4 right-4 p-2 bg-red-500 hover:bg-red-600 text-white rounded-full transition-colors"
              aria-label="End Conversation"
            >
              <X className="w-6 h-6" />
            </button>
          )}

          {/* Session completion message */}
          {currentAudioIndex >= AUDIO_FILES.length && (
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black bg-opacity-75 text-white p-6 rounded-lg text-center">
              <h2 className="text-2xl font-bold mb-2">Session Complete</h2>
              <p>Conversation ended!.</p>
            </div>
          )}
        </>
      )}
    </main>
  )
}

