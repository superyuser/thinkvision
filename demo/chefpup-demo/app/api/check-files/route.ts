import { NextResponse } from "next/server"
import { existsSync } from "fs"
import { join } from "path"

export async function GET() {
  try {
    const uploadDir = join(process.cwd(), "public", "uploads")
    const videoPath = join(uploadDir, "video.mp4")

    // Check if video file exists
    const videoExists = existsSync(videoPath)

    // Check if all 4 audio files exist
    let allAudioFilesExist = true
    for (let i = 1; i <= 4; i++) {
      const audioPath = join(uploadDir, `${i}.mp3`)
      if (!existsSync(audioPath)) {
        allAudioFilesExist = false
        break
      }
    }

    const allFilesExist = videoExists && allAudioFilesExist

    return NextResponse.json({ exist: allFilesExist })
  } catch (error) {
    console.error("Error checking files:", error)
    return NextResponse.json({ exist: false })
  }
}

