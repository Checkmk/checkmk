/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { afterEach, vi } from 'vitest'
import { nextTick } from 'vue'

import GraphTitle from '@/graphing/components/header/GraphTitle.vue'

// Give a rendered GraphTitle a measurable width and line-height, and make its hidden probe report a
// height that only "fits" while the candidate stays within `maxChars` characters. This drives the
// component's fit loop deterministically in jsdom, which otherwise reports zero geometry.
function stubTitleGeometry(root: HTMLElement, probe: HTMLElement, maxChars: number): void {
  Object.defineProperty(root, 'clientWidth', { configurable: true, value: 300 })
  const originalGetComputedStyle = window.getComputedStyle.bind(window)
  vi.stubGlobal('getComputedStyle', (el: Element, pseudo?: string | null) =>
    el === root
      ? ({ lineHeight: '20px' } as CSSStyleDeclaration) // maxHeight = 20 * 2 lines + 1 = 41
      : originalGetComputedStyle(el, pseudo ?? undefined)
  )
  Object.defineProperty(probe, 'scrollHeight', {
    configurable: true,
    get(this: HTMLElement) {
      return (this.textContent?.length ?? 0) <= maxChars ? 40 : 60
    }
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders the title text', () => {
  render(GraphTitle, { props: { title: 'CPU utilization' } })
  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
})

test('renders without error when title is an empty string', () => {
  render(GraphTitle, { props: { title: '' } })
  expect(document.querySelector('.graphing-graph-title')).toBeInTheDocument()
})

test('middle-truncates a title that does not fit, keeping the full text as the tooltip', async () => {
  const fullTitle = 'Very long graph title that certainly does not fit on two lines here'
  const { container, rerender } = render(GraphTitle, { props: { title: 'seed' } })
  const root = container.querySelector<HTMLElement>('.graphing-graph-title')!
  const probe = container.querySelector<HTMLElement>('.graphing-graph-title__probe')!
  stubTitleGeometry(root, probe, 25)

  await rerender({ title: fullTitle })
  await nextTick()

  expect(root.textContent).toContain('…')
  expect(root.textContent!.trim().length).toBeLessThanOrEqual(25)
  // The native tooltip always carries the full, untruncated title.
  expect(root).toHaveAttribute('title', fullTitle)
})

test('shows the full title unchanged when it fits', async () => {
  const { container, rerender } = render(GraphTitle, { props: { title: 'seed' } })
  const root = container.querySelector<HTMLElement>('.graphing-graph-title')!
  const probe = container.querySelector<HTMLElement>('.graphing-graph-title__probe')!
  stubTitleGeometry(root, probe, 25)

  await rerender({ title: 'Short title' })
  await nextTick()

  expect(root.textContent!.trim()).toBe('Short title')
})
