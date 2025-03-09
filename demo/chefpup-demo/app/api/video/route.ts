import { type NextRequest, NextResponse } from "next/server"
import { createReadStream, statSync } from "fs"
import { resolve } from "path"
import { mediaConfig } from "@/config/media-paths"

export async function GET(request: NextRequest) {
  try {
    // Resolve the absolute path to the video file
    const videoPath = resolve(mediaConfig.videoPath)

    // Get file stats
    const stat = statSync(videoPath)
    const fileSize = stat.size

    // Get range from request header
    const range = request.headers.get("range")

    if (range) {
      // Handle range request (streaming)
      const parts = range.replace(/bytes=/, "").split("-")
      const start = Number.parseInt(parts[0], 10)
      const end = parts[1] ? Number.parseInt(parts[1], 10) : fileSize - 1
      const chunkSize = end - start + 1

      const file = createReadStream(videoPath, { start, end })

      // Set appropriate headers for range request
      const headers = {
        "Content-Range": `bytes ${start}-${end}/${fileSize}`,
        "Accept-Ranges": "bytes",
        "Content-Length": chunkSize.toString(),
        "Content-Type": "video/mp4",
      }

      return new NextResponse(file as any, {
        status: 206,
        headers,
      })
    } else {
      // Handle normal request
      const file = createReadStream(videoPath)

      const headers = {
        "Content-Length": fileSize.toString(),
        "Content-Type": "video/mp4",
      }

      return new NextResponse(file as any, {
        status: 200,
        headers,
      })
    }
  } catch (error) {
    console.error("Error serving video:", error)
    return NextResponse.json({ error: "Failed to serve video file" }, { status: 500 })
  }
}

