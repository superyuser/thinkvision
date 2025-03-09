import { type NextRequest, NextResponse } from "next/server"
import { writeFile, mkdir } from "fs/promises"
import { join } from "path"
import { existsSync } from "fs"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()

    // Get the video file
    const videoFile = formData.get("video") as File
    if (!videoFile) {
      return NextResponse.json({ error: "No video file provided" }, { status: 400 })
    }

    // Get the audio files
    const audioFiles: File[] = []
    for (let i = 1; i <= 4; i++) {
      const audioFile = formData.get(`audio${i}`) as File
      if (!audioFile) {
        return NextResponse.json({ error: `Missing audio file ${i}` }, { status: 400 })
      }
      audioFiles.push(audioFile)
    }

    // Create upload directory if it doesn't exist
    const uploadDir = join(process.cwd(), "public", "uploads")
    if (!existsSync(uploadDir)) {
      await mkdir(uploadDir, { recursive: true })
    }

    // Save video file
    const videoBytes = await videoFile.arrayBuffer()
    const videoBuffer = Buffer.from(videoBytes)
    const videoPath = join(uploadDir, "video.mp4")
    await writeFile(videoPath, videoBuffer)

    // Save audio files
    for (let i = 0; i < audioFiles.length; i++) {
      const audioBytes = await audioFiles[i].arrayBuffer()
      const audioBuffer = Buffer.from(audioBytes)
      const audioPath = join(uploadDir, `${i + 1}.mp3`)
      await writeFile(audioPath, audioBuffer)
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("Upload error:", error)
    return NextResponse.json({ error: "Upload failed" }, { status: 500 })
  }
}

