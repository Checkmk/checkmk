/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What Esc and the arrows do when nothing else wants them (CMK-38372). A key some widget,
 * menu or type-to-focus has taken is left alone, and so is one pressed while the focus is
 * outside the view (a slide-in, say).
 *
 * - Esc lets go of the focus, unless its handling has moved the focus already.
 * - The arrows move the focus to the nearest clickable element in their direction, or,
 *   with nothing focused, ArrowUp/ArrowDown scroll the table.
 */
import { type Ref, onBeforeUnmount, onMounted } from 'vue'

import { INTERACTIVE_SELECTOR } from './interactiveSelector'
import { revealInTable } from './revealInTable'

const SCROLL_STEP_PX = 33
/** Borders of neighbours may overlap by this much. */
const TOLERANCE_PX = 2

type Direction = 'ArrowDown' | 'ArrowUp' | 'ArrowLeft' | 'ArrowRight'

/** Elements that give the arrows a meaning of their own. */
const OWNS_ARROWS_SELECTOR = [
  'textarea',
  'select',
  'input:not([type="checkbox"])',
  '[contenteditable]',
  '[role="combobox"]',
  '[role="listbox"]',
  '[role="menu"]',
  '[role="menuitem"]',
  '[role="slider"]',
  '[role="separator"]',
  '[role="dialog"]'
].join(', ')

const CANDIDATE_SELECTOR = `${INTERACTIVE_SELECTOR}, [tabindex]:not([tabindex="-1"])`

const BEYOND: Record<Direction, (from: DOMRect, to: DOMRect) => boolean> = {
  ArrowDown: (from, to) => to.top >= from.bottom - TOLERANCE_PX,
  ArrowUp: (from, to) => to.bottom <= from.top + TOLERANCE_PX,
  ArrowRight: (from, to) => to.left >= from.right - TOLERANCE_PX,
  ArrowLeft: (from, to) => to.right <= from.left + TOLERANCE_PX
}

function isDirection(key: string): key is Direction {
  return Object.hasOwn(BEYOND, key)
}

/** Distance along the direction, with straying off its axis weighing double. */
function distance(from: DOMRect, to: DOMRect, direction: Direction): number {
  const dx = Math.abs(to.left + to.width / 2 - (from.left + from.width / 2))
  const dy = Math.abs(to.top + to.height / 2 - (from.top + from.height / 2))
  return direction === 'ArrowDown' || direction === 'ArrowUp' ? dy + 2 * dx : dx + 2 * dy
}

function nearest(scope: HTMLElement, from: Element, direction: Direction): HTMLElement | null {
  const origin = from.getBoundingClientRect()
  return [...scope.querySelectorAll<HTMLElement>(CANDIDATE_SELECTOR)]
    .filter((element) => element !== from && !element.closest('[aria-hidden="true"]'))
    .map((element) => ({ element, rect: element.getBoundingClientRect() }))
    .filter(({ rect }) => rect.width > 0 && rect.height > 0 && BEYOND[direction](origin, rect))
    .map(({ element, rect }) => ({ element, score: distance(origin, rect, direction) }))
    .reduce<{ element: HTMLElement | null; score: number }>(
      (best, candidate) => (candidate.score < best.score ? candidate : best),
      { element: null, score: Infinity }
    ).element
}

function hasModifier(event: KeyboardEvent): boolean {
  return event.ctrlKey || event.altKey || event.metaKey || event.shiftKey
}

export function useFallbackKeys(
  scope: Readonly<Ref<HTMLElement | null>>,
  container: () => HTMLElement | null | undefined
): void {
  /** Focused when Esc went down, before anyone handled it. */
  let focusedOnEscape: Element | null = null

  const inScope = (element: Element | null): element is HTMLElement =>
    element instanceof HTMLElement && element !== document.body && !!scope.value?.contains(element)

  function moveFocus(active: HTMLElement, direction: Direction, event: KeyboardEvent): void {
    const target = active.closest(OWNS_ARROWS_SELECTOR)
      ? null
      : nearest(scope.value!, active, direction)
    if (target) {
      event.preventDefault()
      target.focus({ preventScroll: true })
      revealInTable(target, container())
    }
  }

  function scrollTable(direction: Direction, event: KeyboardEvent): void {
    const element = direction === 'ArrowDown' || direction === 'ArrowUp' ? container() : null
    if (element) {
      event.preventDefault()
      element.scrollBy({ top: direction === 'ArrowDown' ? SCROLL_STEP_PX : -SCROLL_STEP_PX })
    }
  }

  function onKeyDownCapture(event: KeyboardEvent): void {
    focusedOnEscape = event.key === 'Escape' ? document.activeElement : focusedOnEscape
  }

  function onKeyDown(event: KeyboardEvent): void {
    if (event.defaultPrevented || hasModifier(event)) {
      return
    }
    const active = document.activeElement
    if (event.key === 'Escape' && inScope(active) && active === focusedOnEscape) {
      active.blur()
    } else if (isDirection(event.key) && inScope(active)) {
      moveFocus(active, event.key, event)
    } else if (isDirection(event.key) && (!active || active === document.body)) {
      scrollTable(event.key, event)
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeyDownCapture, true)
    window.addEventListener('keydown', onKeyDown)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeyDownCapture, true)
    window.removeEventListener('keydown', onKeyDown)
  })
}
