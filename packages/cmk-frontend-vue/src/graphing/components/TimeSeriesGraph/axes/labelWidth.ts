/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const LABEL_FONT_SIZE_VAR = '--font-size-small'
const FALLBACK_FONT_SIZE_PX = 10
const FALLBACK_EM_PER_CHAR = 0.6

interface LabelFont {
  spec: string
  sizePx: number
  letterSpacingPx: number
}

const fontByReference = new WeakMap<Element, LabelFont>()
const widthByFontAndText = new Map<string, number>()
let sharedContext: CanvasRenderingContext2D | null | undefined

function measurementContext(): CanvasRenderingContext2D | null {
  if (sharedContext === undefined) {
    sharedContext = document.createElement('canvas').getContext('2d')
  }
  return sharedContext
}

function labelFont(reference: Element | null): LabelFont {
  if (!reference) {
    return {
      spec: `${FALLBACK_FONT_SIZE_PX}px sans-serif`,
      sizePx: FALLBACK_FONT_SIZE_PX,
      letterSpacingPx: 0
    }
  }
  const cached = fontByReference.get(reference)
  if (cached) {
    return cached
  }
  const style = getComputedStyle(reference)
  const sizePx = parseFloat(style.getPropertyValue(LABEL_FONT_SIZE_VAR)) || FALLBACK_FONT_SIZE_PX
  const font = {
    spec: `${sizePx}px ${style.fontFamily || 'sans-serif'}`,
    sizePx,
    letterSpacingPx: parseFloat(style.letterSpacing) || 0
  }
  fontByReference.set(reference, font)
  return font
}

export function measureAxisLabel(text: string, reference: Element | null): number {
  const font = labelFont(reference)
  const key = `${font.spec}|${font.letterSpacingPx}|${text}`
  const cached = widthByFontAndText.get(key)
  if (cached !== undefined) {
    return cached
  }
  const context = measurementContext()
  let glyphAdvances = 0
  if (context) {
    context.font = font.spec
    glyphAdvances = context.measureText(text)?.width ?? 0
  }
  if (!glyphAdvances) {
    glyphAdvances = text.length * font.sizePx * FALLBACK_EM_PER_CHAR
  }
  const width = glyphAdvances + text.length * font.letterSpacingPx
  widthByFontAndText.set(key, width)
  return width
}
