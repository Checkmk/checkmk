/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, nextTick } from 'vue'

/** Selection, keyboard and scroll behavior of a single vertical listbox column. */
export function useListboxColumn<T>(args: {
  options: () => readonly T[]
  selected: Ref<T>
  /** The scrollable ancestor of the listbox; centering scrolls this element. */
  scroller: () => HTMLElement | null
  /** The element containing the option buttons. */
  listbox: () => HTMLDivElement | null
  navigate: (direction: 'previous' | 'next') => void
  commit: () => void
}): {
  onKeydown: (event: KeyboardEvent) => void
  focusSelected: () => void
  centerSelected: () => void
} {
  function selectedButton(): HTMLButtonElement | null {
    return args.listbox()?.querySelector('[aria-selected="true"]') ?? null
  }

  function focusSelected(): void {
    void nextTick(() => selectedButton()?.focus())
  }

  /** Center the column on its selected option by scrolling the column itself. Deliberately not
   * `scrollIntoView`, which would also scroll ancestors — opening the picker must never move
   * the page. */
  function centerSelected(): void {
    const scroller = args.scroller()
    const button = selectedButton()
    if (!scroller || !button) {
      return
    }
    const buttonTop = button.getBoundingClientRect().top - scroller.getBoundingClientRect().top
    scroller.scrollTop += buttonTop - (scroller.clientHeight - button.offsetHeight) / 2
  }

  function cycleSelected(delta: 1 | -1): void {
    const options = args.options()
    const currentIndex = options.indexOf(args.selected.value)
    if (currentIndex === -1) {
      // No current selection in the list: step in from the edge — down → first, up → last.
      args.selected.value = delta === 1 ? options[0]! : options[options.length - 1]!
      return
    }
    const nextIndex = (currentIndex + delta + options.length) % options.length
    args.selected.value = options[nextIndex]!
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      cycleSelected(event.key === 'ArrowDown' ? 1 : -1)
      focusSelected()
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      args.navigate('previous')
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      args.navigate('next')
    } else if (event.key === 'Enter') {
      event.preventDefault()
      args.commit()
    }
  }

  return { onKeydown, focusSelected, centerSelected }
}
