/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

function seg(
  label: string,
  count: number,
  color: StateSegment['color'],
  href?: string
): StateSegment {
  return { label: label as TranslatedString, count, color, href }
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
  render(CmkStateCountBar, { props: { segments: MIX } })

  for (const entry of ['OK: 5', 'WARN: 2', 'CRIT: 0', 'UNKNOWN: 1', 'PENDING: 0']) {
    expect(screen.getByText(entry)).toBeInTheDocument()
  }
})

test('a non-zero count links to where its segment points', () => {
  render(CmkStateCountBar, {
    props: { segments: [seg('OK', 5, 'success', 'monitor_host_services.py?host=web-1')] }
  })

  expect(screen.getByRole('link', { name: 'OK: 5' })).toHaveAttribute(
    'href',
    'monitor_host_services.py?host=web-1'
  )
})

test('the total, when given, leads the legend with the summed count', () => {
  render(CmkStateCountBar, {
    props: {
      segments: MIX,
      total: {
        label: 'All services' as TranslatedString,
        href: 'monitor_host_services.py?host=web-1'
      }
    }
  })

  const total = screen.getByRole('link', { name: 'All services: 8' })
  expect(total).toHaveAttribute('href', 'monitor_host_services.py?host=web-1')
  expect(total.compareDocumentPosition(screen.getByText('OK: 5'))).toBe(
    Node.DOCUMENT_POSITION_FOLLOWING
  )
})

test('the legend lists the states alone when no total is given', () => {
  const { container } = render(CmkStateCountBar, { props: { segments: MIX } })

  expect(container.querySelectorAll('.cmk-state-count-bar__legend-item')).toHaveLength(5)
  expect(screen.queryByText(/All services/)).not.toBeInTheDocument()
})

test('a zero count is listed but not linked', () => {
  render(CmkStateCountBar, {
    props: { segments: [seg('CRIT', 0, 'danger', 'monitor_host_services.py?host=web-1')] }
  })

  expect(screen.getByText('CRIT: 0')).toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
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

test('wears the medium size unless a smaller bar is asked for', () => {
  const { container } = render(CmkStateCountBar, { props: { segments: MIX } })

  expect(container.querySelector('.cmk-state-count-bar')).toHaveClass(
    'cmk-state-count-bar--size-medium'
  )
})

test('thins the bar down to the small size on request', () => {
  const { container } = render(CmkStateCountBar, { props: { segments: MIX, size: 'small' } })

  expect(container.querySelector('.cmk-state-count-bar')).toHaveClass(
    'cmk-state-count-bar--size-small'
  )
})
