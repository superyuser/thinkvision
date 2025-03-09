import { type NextRequest, NextResponse } from "next/server"
import { createReadStream, statSync } from "fs"
import { join, resolve } from "path"

// Base directory for audio files
const AUDIO_BASE_DIR = "C:\Users\Bubble\Desktop\dog-audios"

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  try {
    const id = params.id

    // Make sure the ID is valid (1-5)
    if (!id || isNaN(Number(id)) || Number(id) < 1 || Number(id) > 5) {
      return NextResponse.json({ error: "Invalid audio file ID" }, { status: 400 })
    }

    // Get the audio file path
    const audioFileName = `${id}.wav`
    const audioPath = resolve(join(AUDIO_BASE_DIR, audioFileName))

    // Get file stats
    const stat = statSync(audioPath)
    const fileSize = stat.size

    // Create read stream
    const file = createReadStream(audioPath)

    const headers = {
      "Content-Length": fileSize.toString(),
      "Content-Type": "audio/wav",
    }

    return new NextResponse(file as any, {
      status: 200,
      headers,
    })
  } catch (error) {
    console.error("Error serving audio:", error)
    return NextResponse.json({ error: "Failed to serve audio file" }, { status: 500 })
  }
}

