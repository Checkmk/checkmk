/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { nextTick } from 'vue'

/** Focus controller over an ordered list of segment inputs. `keys` returns the current segment
 *  order, read fresh on each move (the order changes with the date format, e.g. DMY ↔ MDY). */
export function useSegmentFocus(
  keys: () => string[],
  navigateOut: (direction: -1 | 1) => void
): {
  registerInput: (key: string, el: HTMLInputElement | null) => void
  moveFocus: (key: string, delta: 1 | -1) => void
  focusFirst: () => void
  focusLast: () => void
} {
  // Imperative element handles; not reactive (only read to call .focus()/.select()).
  const elements: Record<string, HTMLInputElement | null> = {}

  function registerInput(key: string, el: HTMLInputElement | null): void {
    elements[key] = el
  }

  function focusKey(key: string | undefined): void {
    if (key === undefined) {
      return
    }
    void nextTick(() => {
      const element = elements[key]
      element?.focus()
      element?.select()
    })
  }

  function moveFocus(key: string, delta: 1 | -1): void {
    const order = keys()
    const neighbor = order[order.indexOf(key) + delta]
    if (neighbor === undefined) {
      navigateOut(delta)
      return
    }
    focusKey(neighbor)
  }

  function focusFirst(): void {
    focusKey(keys()[0])
  }

  function focusLast(): void {
    focusKey(keys().at(-1))
  }

  return { registerInput, moveFocus, focusFirst, focusLast }
}
