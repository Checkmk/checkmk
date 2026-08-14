/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { type Ref, defineComponent, h, nextTick, ref } from 'vue'

import { useHeaderLineBreakLevel } from '@/graphing/components/private/useHeaderLineBreakLevel'

// jsdom has no ResizeObserver and does no layout, so stub the observer and feed every element its
// geometry by hand (getBoundingClientRect + the title's computed line-height).
class FakeResizeObserver {
  static instances: FakeResizeObserver[] = []
  constructor(public callback: ResizeObserverCallback) {
    FakeResizeObserver.instances.push(this)
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

interface Rect {
  top: number
  height: number
  width: number
}

function stubRect(el: HTMLElement, rect: Rect): void {
  Object.defineProperty(el, 'getBoundingClientRect', {
    configurable: true,
    value: () =>
      ({
        top: rect.top,
        bottom: rect.top + rect.height,
        height: rect.height,
        width: rect.width,
        left: 0,
        right: rect.width,
        x: 0,
        y: rect.top,
        toJSON: () => ({})
      }) as DOMRect
  })
}

interface Layout {
  header: Rect
  title: Rect
  valuesAndTime: Rect
  zoomAndMenu: Rect
  titleLineHeight: number
}

interface Flags {
  showTitle?: boolean
  showValuesAndTime?: boolean
  showZoomAndMenu?: boolean
}

type Block = 'header' | 'title' | 'valuesAndTime' | 'zoomAndMenu'

function setupHeaderLineBreakLevel(layout: Layout, flags: Flags = {}) {
  const els: Record<Block, HTMLElement> = {
    header: document.createElement('div'),
    title: document.createElement('div'),
    valuesAndTime: document.createElement('div'),
    zoomAndMenu: document.createElement('div')
  }
  stubRect(els.header, layout.header)
  stubRect(els.title, layout.title)
  stubRect(els.valuesAndTime, layout.valuesAndTime)
  stubRect(els.zoomAndMenu, layout.zoomAndMenu)

  const originalGetComputedStyle = window.getComputedStyle.bind(window)
  vi.stubGlobal('getComputedStyle', (el: Element, pseudo?: string | null) =>
    el === els.title
      ? ({ lineHeight: `${layout.titleLineHeight}px` } as CSSStyleDeclaration)
      : originalGetComputedStyle(el, pseudo ?? undefined)
  )

  const showTitle = ref(flags.showTitle ?? true)
  const showValuesAndTime = ref(flags.showValuesAndTime ?? true)
  const showZoomAndMenu = ref(flags.showZoomAndMenu ?? true)

  let headerLineBreakLevel!: Ref<number>
  const host = defineComponent({
    setup() {
      ;({ headerLineBreakLevel } = useHeaderLineBreakLevel(
        {
          headerRef: ref(els.header),
          titleRef: ref(els.title),
          valuesAndTimeRef: ref(els.valuesAndTime),
          zoomAndMenuRef: ref(els.zoomAndMenu)
        },
        {
          showTitle: () => showTitle.value,
          showValuesAndTime: () => showValuesAndTime.value,
          showZoomAndMenu: () => showZoomAndMenu.value
        }
      ))
      return () => h('div')
    }
  })
  render(host)

  return {
    level: () => headerLineBreakLevel.value,
    setRect: (block: Block, rect: Rect) => stubRect(els[block], rect),
    showTitle,
    showValuesAndTime,
    showZoomAndMenu
  }
}

// Single-line row rects at increasing vertical offsets; individual tests move blocks onto other rows.
// THIRD_ROW clears a two-line (45px) title so the two never vertically overlap.
const FIRST_ROW: Rect = { top: 0, height: 20, width: 120 }
const SECOND_ROW: Rect = { top: 40, height: 20, width: 120 }
const THIRD_ROW: Rect = { top: 60, height: 20, width: 120 }

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

test('level 0: every block shares one row and the title is a single line', () => {
  const { level } = setupHeaderLineBreakLevel({
    header: { top: 0, height: 20, width: 800 },
    title: FIRST_ROW,
    valuesAndTime: FIRST_ROW,
    zoomAndMenu: FIRST_ROW,
    titleLineHeight: 20
  })
  expect(level()).toBe(0)
})

test('level 0: no measurable width yet holds the level at 0', () => {
  const { level } = setupHeaderLineBreakLevel({
    header: { top: 0, height: 0, width: 0 },
    title: { top: 0, height: 45, width: 200 }, // would read as multi-line if width were measurable
    valuesAndTime: SECOND_ROW,
    zoomAndMenu: FIRST_ROW,
    titleLineHeight: 20
  })
  expect(level()).toBe(0)
})

test('level 1: values-and-time drops to its own row while title and zoom stay together', () => {
  const { level } = setupHeaderLineBreakLevel({
    header: { top: 0, height: 60, width: 800 },
    title: FIRST_ROW,
    valuesAndTime: SECOND_ROW,
    zoomAndMenu: FIRST_ROW,
    titleLineHeight: 20
  })
  expect(level()).toBe(1)
})

test('level 1: a hidden zoom-and-menu resolves to level 1 rather than wrapping the title', () => {
  const { level } = setupHeaderLineBreakLevel(
    {
      header: { top: 0, height: 60, width: 400 },
      title: { top: 0, height: 45, width: 380 }, // multi-line, so not level 0
      valuesAndTime: SECOND_ROW,
      zoomAndMenu: FIRST_ROW,
      titleLineHeight: 20
    },
    { showZoomAndMenu: false }
  )
  expect(level()).toBe(1)
})

test('level 1: a hidden title resolves to level 1', () => {
  const { level } = setupHeaderLineBreakLevel(
    {
      header: { top: 0, height: 60, width: 800 },
      title: FIRST_ROW,
      valuesAndTime: SECOND_ROW,
      zoomAndMenu: FIRST_ROW,
      titleLineHeight: 20
    },
    { showTitle: false }
  )
  expect(level()).toBe(1)
})

test('level 2: title and zoom can no longer share a row', () => {
  const { level } = setupHeaderLineBreakLevel({
    header: { top: 0, height: 100, width: 400 },
    title: { top: 0, height: 45, width: 380 },
    valuesAndTime: { top: 90, height: 20, width: 120 },
    zoomAndMenu: THIRD_ROW, // its own row, clear of the two-line title
    titleLineHeight: 20
  })
  expect(level()).toBe(2)
})

test('level 2 holds while the title stays multi-line (hysteresis)', async () => {
  const header = setupHeaderLineBreakLevel({
    header: { top: 0, height: 100, width: 400 },
    title: { top: 0, height: 45, width: 380 },
    valuesAndTime: { top: 90, height: 20, width: 120 },
    zoomAndMenu: THIRD_ROW,
    titleLineHeight: 20
  })
  expect(header.level()).toBe(2)

  // Force a recompute (a show* change) without changing the title's wrapping: level 2 must persist.
  header.showValuesAndTime.value = false
  await nextTick()
  await nextTick()
  expect(header.level()).toBe(2)
})

test('level 2 releases to level 1 once the title fits a single line again', async () => {
  const header = setupHeaderLineBreakLevel({
    header: { top: 0, height: 100, width: 400 },
    title: { top: 0, height: 45, width: 380 },
    valuesAndTime: { top: 90, height: 20, width: 120 },
    zoomAndMenu: THIRD_ROW,
    titleLineHeight: 20
  })
  expect(header.level()).toBe(2)

  header.setRect('title', { top: 0, height: 20, width: 380 }) // now a single line
  header.showValuesAndTime.value = false // trigger a recompute
  await nextTick()
  await nextTick()
  expect(header.level()).toBe(1)
})

test('level 0: only the zoom-and-menu shown collapses to a single row', () => {
  const { level } = setupHeaderLineBreakLevel(
    {
      header: { top: 0, height: 20, width: 800 },
      title: FIRST_ROW,
      valuesAndTime: FIRST_ROW,
      zoomAndMenu: FIRST_ROW,
      titleLineHeight: 20
    },
    { showTitle: false, showValuesAndTime: false }
  )
  expect(level()).toBe(0)
})
