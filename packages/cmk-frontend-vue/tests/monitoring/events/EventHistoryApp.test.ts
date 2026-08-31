/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { afterAll, beforeAll, expect, test } from 'vitest'
import { nextTick } from 'vue'

import EventHistoryApp from '@/monitoring/events/EventHistoryApp.vue'
import type { EventEntry, EventsResponse } from '@/monitoring/events/api'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

// MonitoringTable virtualizes off its own wrapper, which jsdom measures as zero-sized;
// without a height no row would be rendered at all.
const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
})

afterAll(() => {
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
  if (originalOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  }
})

const HISTORY_LINK = 'view.py?view_name=hostsvcevents&site=local&host=web-1'

const SECONDS_PER_DAY = 24 * 60 * 60

/** The window's start is only handed out as a timestamp, so the tests anchor it to now. */
function since(days: number): number {
  return Math.floor(Date.now() / 1000) - days * SECONDS_PER_DAY
}

function makeEvent(overrides: Partial<EventEntry> = {}): EventEntry {
  return {
    time: 1752405510,
    event: 'SERVICE ALERT',
    service_name: 'CPU load',
    state_info: 'OK - CRITICAL',
    plugin_output: 'CRIT - load average: 12.0',
    icon: { icon_name: 'alert-crit', title: 'Service alert' },
    ...overrides
  }
}

function mountTab(data: Partial<EventsResponse> = {}, subject: 'host' | 'service' = 'host') {
  return render(EventHistoryApp, {
    props: {
      subject,
      data: {
        events: [],
        meta: {
          limit: 500,
          truncated: false,
          since: since(8),
          time_window_days: 8,
          legacy_events_link: HISTORY_LINK
        },
        ...data
      }
    }
  })
}

/** MonitoringTable's virtualizer needs a tick to measure before it hands out rows. */
async function flushVirtualizer(): Promise<void> {
  await nextTick()
  await nextTick()
}

test('an event is listed with its icon, event, service, state information and output', async () => {
  mountTab({ events: [makeEvent()] })
  await flushVirtualizer()

  // Cell text carries zero-width breaks (`useSoftBreak`), so the cells are matched by
  // the raw value they keep in their `title` - as the other row tests do.
  expect(screen.getByRole('img', { name: 'Service alert' })).toBeInTheDocument()
  expect(screen.getByTitle('SERVICE ALERT')).toBeInTheDocument()
  expect(screen.getByTitle('CPU load')).toBeInTheDocument()
  expect(screen.getByTitle('OK - CRITICAL')).toBeInTheDocument()
  expect(screen.getByTitle('CRIT - load average: 12.0')).toBeInTheDocument()
})

test('the event icon is read-only: it links nowhere', async () => {
  mountTab({ events: [makeEvent()] })
  await flushVirtualizer()

  expect(screen.queryByRole('link', { name: 'Service alert' })).not.toBeInTheDocument()
})

test('the time column carries the date, so a flat list needs no per-day grouping', async () => {
  // Asserted as a shape rather than a literal: `formatTimestamp` renders local time and
  // the test suite pins no timezone.
  mountTab({ events: [makeEvent({ time: 1752405510 })] })
  await flushVirtualizer()

  expect(screen.getByTitle(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)).toBeInTheDocument()
  expect(screen.queryByTitle('1752405510')).not.toBeInTheDocument()
})

test('the events keep the order the API sent them in', async () => {
  mountTab({
    events: [
      makeEvent({ plugin_output: 'newest' }),
      makeEvent({ plugin_output: 'older' }),
      makeEvent({ plugin_output: 'oldest' })
    ]
  })
  await flushVirtualizer()

  const rows = screen.getAllByRole('row').map((row) => row.textContent ?? '')

  expect(rows.filter((row) => row.includes('newest')).length).toBe(1)
  expect(rows.findIndex((row) => row.includes('newest'))).toBeLessThan(
    rows.findIndex((row) => row.includes('older'))
  )
  expect(rows.findIndex((row) => row.includes('older'))).toBeLessThan(
    rows.findIndex((row) => row.includes('oldest'))
  )
})

test('an event kind the API resolved no icon for still renders its row', async () => {
  mountTab({ events: [makeEvent({ icon: null, event: 'TIMEPERIOD TRANSITION' })] })
  await flushVirtualizer()

  expect(screen.getByTitle('TIMEPERIOD TRANSITION')).toBeInTheDocument()
})

test('a host without events in the window is explained rather than shown an empty table', () => {
  mountTab()

  expect(screen.getByText('No events in the last 8 days.')).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

test('the empty explanation does not repeat the subject already named in the header above it', () => {
  mountTab({}, 'service')

  expect(screen.getByText('No events in the last 8 days.')).toBeInTheDocument()
  expect(screen.getByText(/^Events of the last 8 days for this service/)).toBeInTheDocument()
})

test('the service column is dropped for a service, whose rows would all repeat its name', async () => {
  mountTab({ events: [makeEvent()] }, 'service')
  await flushVirtualizer()

  expect(screen.queryByTitle('CPU load')).not.toBeInTheDocument()
  expect(screen.getByTitle('SERVICE ALERT')).toBeInTheDocument()
})

test('an event of the host itself is marked as such in the service column', async () => {
  mountTab({ events: [makeEvent({ event: 'HOST ALERT', service_name: null })] })
  await flushVirtualizer()

  expect(screen.getByText('Host')).toBeInTheDocument()
})

test('a list the row limit cut off says so', () => {
  mountTab({
    events: [makeEvent()],
    meta: {
      limit: 1,
      truncated: true,
      since: since(8),
      time_window_days: 8,
      legacy_events_link: HISTORY_LINK
    }
  })

  expect(
    screen.getByText('Only the 1 most recent events are shown. Open the full history for more.')
  ).toBeInTheDocument()
})

test('a list that fits is not announced as cut off', () => {
  mountTab({ events: [makeEvent()] })

  expect(screen.queryByText(/most recent events are shown/)).not.toBeInTheDocument()
})

test('the tab links to the legacy history view the API resolved for its subject', () => {
  mountTab({ events: [makeEvent()] })

  const link = screen.getByRole('link', { name: /Show all events/ })

  expect(link).toHaveAttribute('href', HISTORY_LINK)
  expect(link).toHaveAttribute('target', '_top')
})

test('the explained window follows what the API applied, not a hard-coded eight days', () => {
  mountTab({
    meta: {
      limit: 500,
      truncated: false,
      since: since(2),
      time_window_days: 2,
      legacy_events_link: HISTORY_LINK
    }
  })

  expect(screen.getByText('No events in the last 2 days.')).toBeInTheDocument()
})

test('the header states the window and its start, next to the legacy history link', () => {
  mountTab({
    events: [makeEvent()],
    meta: {
      limit: 500,
      truncated: false,
      since: since(8),
      time_window_days: 8,
      legacy_events_link: HISTORY_LINK
    }
  })

  // Asserted as a shape rather than a literal: `formatTimestamp` renders local time and
  // the test suite pins no timezone.
  expect(
    screen.getByText(
      /^Events of the last 8 days for this host \(since \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)$/
    )
  ).toBeInTheDocument()
})

test('the header speaks of the service when that is the subject', () => {
  mountTab({ events: [makeEvent()] }, 'service')

  expect(screen.getByText(/^Events of the last 8 days for this service/)).toBeInTheDocument()
})

test('a list that is not truncated states the full requested window, not just its oldest event', () => {
  mountTab({
    events: [makeEvent({ time: since(1) })],
    meta: {
      limit: 500,
      truncated: false,
      since: since(8),
      time_window_days: 8,
      legacy_events_link: HISTORY_LINK
    }
  })

  expect(screen.getByText(/^Events of the last 8 days for this host/)).toBeInTheDocument()
})

test('a truncated list shows its since as its oldest shown event, not the full requested window', () => {
  const oldestShownTime = 1752000000
  mountTab({
    events: [makeEvent({ time: 1752405510 }), makeEvent({ time: oldestShownTime })],
    meta: {
      limit: 2,
      truncated: true,
      since: since(8),
      time_window_days: 8,
      legacy_events_link: HISTORY_LINK
    }
  })

  expect(
    screen.getByText(
      `Events of the last 8 days for this host (since ${formatTimestamp(oldestShownTime)})`
    )
  ).toBeInTheDocument()
})

// The day count itself is never recomputed here: meta.time_window_days already accounts for
// truncation (see EventHistoryApp.vue and its backend counterpart, _covered_window_days in
// cmk/gui/monitor/hosts/_api/_events.py), so the component only has to display it verbatim.
test('the window info uses the API-reported day count even when the response is truncated', () => {
  mountTab({
    events: [makeEvent()],
    meta: {
      limit: 1,
      truncated: true,
      since: since(8),
      time_window_days: 3,
      legacy_events_link: HISTORY_LINK
    }
  })

  expect(screen.getByText(/^Events of the last 3 days for this host/)).toBeInTheDocument()
})
