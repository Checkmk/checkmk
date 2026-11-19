/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach } from 'vitest'

/**
 * Gives the page a size for the tests of the surrounding describe, so the rows lay out, and with
 * `slideIns` a content area for the slide-ins to open in.
 */
export function layOutThePage({ slideIns }: { slideIns: boolean }): void {
  const originalOffsetHeight = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'offsetHeight'
  )
  const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

  let contentArea: HTMLElement | null = null

  beforeEach(() => {
    if (slideIns) {
      contentArea = document.createElement('div')
      contentArea.id = 'content_area'
      document.body.appendChild(contentArea)
    }
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
  })

  afterEach(() => {
    contentArea?.remove()
    contentArea = null
    if (originalOffsetHeight) {
      Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
    }
    if (originalOffsetWidth) {
      Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
    }
  })
}
