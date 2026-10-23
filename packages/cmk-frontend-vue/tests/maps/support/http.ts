/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** Everything the assertions need from an intercepted request. */
export interface SeenRequest {
  url: URL
  method: string
  headers: Headers
  body: string
}

export async function snapshot(request: Request): Promise<SeenRequest> {
  return {
    url: new URL(request.url),
    method: request.method,
    headers: request.headers,
    body: await request.text()
  }
}
