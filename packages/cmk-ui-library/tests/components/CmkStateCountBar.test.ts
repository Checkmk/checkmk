/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

function seg(label: string, count: number, color: StateSegment['color']): StateSegment {
  return { label: label as TranslatedString, count, color }
}

const MIX: StateSegment[] = [
  seg('OK', 5, 'success'),
  seg('WARN', 2, 'warning'),
  seg('CRIT', 0, 'danger'),
  seg('UNKNOWN', 1, 'unknown'),
  seg('PENDING', 0, 'pending')
]

test('renders one bar segment per non-zero count, sized proportionally', () => {
  render(CmkStateCountBar, { props: { segments: MIX } })

  const bar = screen.getByRole('img')
  const segments = bar.querySelectorAll<HTMLElement>('.cmk-state-count-bar__segment')

  expect(segments).toHaveLength(3) // OK, WARN, UNKNOWN — the two zero counts are omitted
  expect(segments[0]!.style.flexGrow).toBe('5')
  expect(segments[1]!.style.flexGrow).toBe('2')
  expect(segments[2]!.style.flexGrow).toBe('1')
  expect(segments[0]).toHaveClass('cmk-state-count-bar__segment--success')
  expect(segments[1]).toHaveClass('cmk-state-count-bar__segment--warning')
  expect(segments[2]).toHaveClass('cmk-state-count-bar__segment--unknown')
})

test('zero-count state is absent from the bar but still listed in the legend', () => {
  const { container } = render(CmkStateCountBar, { props: { segments: MIX } })

  const bar = screen.getByRole('img')
  expect(bar.querySelector('.cmk-state-count-bar__segment--danger')).toBeNull()

  const legendItems = container.querySelectorAll('.cmk-state-count-bar__legend-item')
  expect(legendItems).toHaveLength(5)
})

test('legend shows each state label with its count', () => {
  const { container } = render(CmkStateCountBar, { props: { segments: MIX } })

  const legendItems = container.querySelectorAll<HTMLElement>('.cmk-state-count-bar__legend-item')
  const expected: [string, string][] = [
    ['OK', '5'],
    ['WARN', '2'],
    ['CRIT', '0'],
    ['UNKNOWN', '1'],
    ['PENDING', '0']
  ]
  expected.forEach(([label, count], index) => {
    const item = within(legendItems[index]!)
    expect(item.getByText(label)).toBeInTheDocument()
    expect(item.getByText(count)).toBeInTheDocument()
  })
})

test('summarizes the counts in the bar aria-label', () => {
  render(CmkStateCountBar, { props: { segments: MIX } })

  expect(screen.getByRole('img')).toHaveAttribute('aria-label', '5 OK, 2 WARN, 1 UNKNOWN')
})

test('all-zero total renders a single neutral track and an empty aria-label', () => {
  const allZero = MIX.map((segment) => ({ ...segment, count: 0 }))
  const { container } = render(CmkStateCountBar, { props: { segments: allZero } })

  const segments = container.querySelectorAll('.cmk-state-count-bar__segment')
  expect(segments).toHaveLength(1)
  expect(segments[0]).toHaveClass('cmk-state-count-bar__segment--empty')
  expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'No services')
})
