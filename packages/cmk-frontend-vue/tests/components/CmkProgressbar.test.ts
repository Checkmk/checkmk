/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, render } from '@testing-library/vue'
import CmkProgressbar from '@/components/CmkProgressbar.vue'

function getRandomProgressValues(): { max: number; value: number } {
  let max = Math.round(Math.random() * 1000)
  max = max === 0 ? 1000 : max
  const value = Math.round(Math.random() * max)
  return { max, value }
}

function ensureProgressIndicatorAt(progressbar: HTMLElement, max: number, value: number): void {
  const progressIndicator = progressbar.querySelector('.cmk-progressbar-indicator')
  expect((progressIndicator as HTMLDivElement).style.transform).toBe(
    `translateX(-${100 - (value / max) * 100}%)`
  )
}

test('Progressbar renders infinite without label', async () => {
  render(CmkProgressbar, {
    props: { max: 'unknown' }
  })

  const progressbar = screen.getByRole('progressbar')

  expect(progressbar.title).toBe('unknown progress')
  expect(progressbar.querySelector('.cmk-progressbar-indicator-infinite')).toBeDefined()
})

test('Progressbar renders to certain progress', async () => {
  const { max, value } = getRandomProgressValues()
  render(CmkProgressbar, {
    props: { max, value }
  })

  const progressbar = screen.getByRole('progressbar')

  expect(progressbar.title).toBe(value.toString())

  ensureProgressIndicatorAt(progressbar, max, value)
})

test('Progressbar renders to certain progress with label', async () => {
  const { max, value } = getRandomProgressValues()
  render(CmkProgressbar, {
    props: { max, value, label: true }
  })

  const progressbar = screen.getByRole('progressbar')

  expect(progressbar.title).toBe(value.toString())
  expect(screen.getByText(value.toString())).toBeDefined()
})

test('Progressbar renders to certain progress with full label', async () => {
  const { max, value } = getRandomProgressValues()
  const unit = 'testunit'
  render(CmkProgressbar, {
    props: { max, value, label: { showTotal: true, unit } }
  })

  const progressbar = screen.getByRole('progressbar')

  expect(progressbar.title).toBe(`${value} / ${max} ${unit}`)
  expect(screen.getByText(`${value} / ${max} ${unit}`)).toBeDefined()

  ensureProgressIndicatorAt(progressbar, max, value)
})
