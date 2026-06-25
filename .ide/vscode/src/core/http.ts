/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as http from 'http'
import * as https from 'https'

function probe(url: string, perTryTimeoutMs: number): Promise<boolean> {
  return new Promise((resolve) => {
    const lib = url.startsWith('https:') ? https : http
    const req = lib.get(url, (res) => {
      res.resume()
      resolve(true)
    })
    req.on('error', () => resolve(false))
    req.setTimeout(perTryTimeoutMs, () => {
      req.destroy()
      resolve(false)
    })
  })
}

// Poll a URL until it answers (any HTTP response counts as "up"), giving a
// freshly started dev server time to bind its port. Resolves true on the first
// successful response, or false once the overall deadline passes.
export async function waitForHttp(
  url: string,
  timeoutMs = 60000,
  intervalMs = 500,
  perTryTimeoutMs = 2000
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await probe(url, perTryTimeoutMs)) return true
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return false
}
