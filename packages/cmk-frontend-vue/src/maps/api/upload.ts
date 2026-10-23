/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How a picked file reaches the server.
 *
 * The REST API speaks JSON, so a file travels base64-encoded in the body rather
 * than as multipart. Every upload Maps offers is capped server-side, and the
 * endpoint refuses an oversized one on the encoded length before decoding it.
 */

interface UploadedFile {
  filename: string
  content_type: string
  /** The file's bytes, base64-encoded. */
  content: string
}

/**
 * The file's bytes as base64.
 *
 * ``readAsDataURL`` is what does the encoding natively, in one pass over the
 * file, instead of walking it in JS — it answers ``data:<type>;base64,<data>``,
 * of which only the payload is wanted.
 */
function encodeFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(reader.error ?? new Error(`Could not read ${file.name}`))
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '')
    reader.readAsDataURL(file)
  })
}

export async function uploadedFile(file: File): Promise<UploadedFile> {
  return {
    filename: file.name,
    // What the browser inferred; the server decides by the file's magic bytes.
    content_type: file.type,
    content: await encodeFile(file)
  }
}
