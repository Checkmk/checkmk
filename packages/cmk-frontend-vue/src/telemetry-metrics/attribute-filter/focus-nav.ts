/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const FOCUSABLE = '[role="combobox"], button, [tabindex]'

// A participant's focusable element: itself, or its first focusable descendant (e.g. a wrapped combobox).
function focusTarget(item: HTMLElement): HTMLElement | null {
  return item.matches(FOCUSABLE) ? item : item.querySelector<HTMLElement>(FOCUSABLE)
}

// ArrowLeft/Right cycle the `[data-af-item]`s of the innermost `[data-af-scope]`, wrapping, never leaving it.
export function handleArrowNav(event: KeyboardEvent): void {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {
    return
  }
  const active = document.activeElement as HTMLElement | null
  const scope = active?.closest<HTMLElement>('[data-af-scope]') ?? null
  if (active === null || scope === null) {
    return
  }
  const items = Array.from(scope.querySelectorAll<HTMLElement>('[data-af-item]')).filter(
    (el) => el.closest('[data-af-scope]') === scope
  )
  // Act only when focus rests on a participant, leaving arrows to an open dropdown's filter input.
  const idx = items.findIndex((item) => focusTarget(item) === active)
  if (idx === -1) {
    return
  }
  event.preventDefault()
  event.stopPropagation()
  const delta = event.key === 'ArrowRight' ? 1 : -1
  focusTarget(items[(idx + delta + items.length) % items.length]!)?.focus()
}
