/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** Offers `blob` to the browser as a download named `filename`. */
export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
  // Revoking straight after click() relies on the download fetch having started
  // during click dispatch, which holds in current Chrome and Firefox but is not
  // guaranteed. Yielding a task first lets the download start on every engine
  // before the URL goes away.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
