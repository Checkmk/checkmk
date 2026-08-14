/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const ELLIPSIS = '…'

// Largest "head ... tail" of whole words (the ellipsis spaced on both sides) that still fits: keep the
// start and the end and drop middle words. Binary search the number of kept words, split between head
// and tail.
function fitByWords(words: string[], fits: (candidate: string) => boolean): string {
  let lo = 1
  let hi = words.length - 1
  let best = ELLIPSIS
  while (lo <= hi) {
    const keep = (lo + hi) >> 1
    const head = words.slice(0, Math.ceil(keep / 2)).join(' ')
    const tail = words.slice(words.length - Math.floor(keep / 2)).join(' ')
    const candidate = tail === '' ? `${head} ${ELLIPSIS}` : `${head} ${ELLIPSIS} ${tail}`
    if (fits(candidate)) {
      best = candidate
      lo = keep + 1
    } else {
      hi = keep - 1
    }
  }
  return best
}

// Fallback for a single over-long word with no boundaries to break on: largest "head...tail" split on
// characters.
function fitByChars(full: string, fits: (candidate: string) => boolean): string {
  let lo = 0
  let hi = full.length
  let best = ELLIPSIS
  while (lo <= hi) {
    const keep = (lo + hi) >> 1
    const head = full.slice(0, Math.ceil(keep / 2))
    const tail = full.slice(full.length - Math.floor(keep / 2))
    const candidate = `${head}${ELLIPSIS}${tail}`
    if (fits(candidate)) {
      best = candidate
      lo = keep + 1
    } else {
      hi = keep - 1
    }
  }
  return best
}

/**
 * Middle-truncate `text` to the largest form that satisfies `fits`, keeping the start and the end and
 * dropping the centre behind an ellipsis. Whole words are dropped first so the ellipsis always sits
 * between two words (a space on each side); a single over-long word falls back to a character split.
 *
 * `fits` is the caller's own fit predicate - typically a DOM measurement
 */
export function middleTruncate(text: string, fits: (candidate: string) => boolean): string {
  if (fits(text)) {
    return text
  }
  const words = text.split(/\s+/).filter((word) => word.length > 0)
  return words.length > 1 ? fitByWords(words, fits) : fitByChars(text, fits)
}
