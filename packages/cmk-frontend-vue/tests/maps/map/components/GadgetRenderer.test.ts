/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import GadgetRenderer from '@/maps/map/components/GadgetRenderer.vue'
import type { MetricUnitMap, ObjectState } from '@/maps/types/api'

import { aState } from '../../support/fixtures'

function makeState(overrides: Partial<ObjectState> = {}): ObjectState {
  return aState({
    object_id: 'srv-01;Memory',
    type: 'service',
    state: 'OK',
    output: 'Memory OK',
    perf_data: 'mem_used=8927830016B;;;0;17179869184',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    ...overrides
  })
}

const units: MetricUnitMap = {
  mem_used: { notation: 'iec', symbol: 'B', precision: { type: 'auto', digits: 2 }, scale: 1 }
}

describe('GadgetRenderer value gadget', () => {
  it('renders the registry-formatted reading in the state colour', () => {
    render(GadgetRenderer, {
      props: {
        type: 'value',
        state: makeState({ state: 'CRITICAL' }),
        size: 60,
        metricUnits: units
      }
    })

    const raw = screen.getByText('8.31 GiB')
    // CRITICAL red from the canonical state palette.
    expect(raw).toHaveStyle({ color: 'rgb(248, 113, 113)' })
  })

  it('falls back to the SI heuristic without a registry entry', () => {
    render(GadgetRenderer, {
      props: { type: 'value', state: makeState(), size: 60 }
    })
    expect(screen.getByText('8.93 GB')).toBeInTheDocument()
  })

  it('renders a dash when the state carries no metrics', () => {
    render(GadgetRenderer, {
      props: { type: 'value', state: makeState({ perf_data: '' }), size: 60 }
    })
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('picks the requested metric out of multi-metric perfdata', () => {
    render(GadgetRenderer, {
      props: {
        type: 'value',
        metric: 'mem_used',
        state: makeState({ perf_data: 'pagefile=1234B;;;; mem_used=8927830016B;;;;' }),
        size: 60,
        metricUnits: units
      }
    })
    expect(screen.getByText('8.31 GiB')).toBeInTheDocument()
  })
})

describe('GadgetRenderer gauge readout', () => {
  // CPU load's load1 carries a `max` (the core count) purely to scale the bar —
  // Checkmk shows it as the absolute load, never a percent. The gauge readout
  // must echo the CMK-formatted value, not fabricate "27%" from value/max.
  it('shows the absolute value for a max-bearing non-% metric', () => {
    render(GadgetRenderer, {
      props: {
        type: 'gauge',
        metric: 'load1',
        state: makeState({ perf_data: 'load1=1.09;;;0;4', state: 'OK' }),
        size: 120,
        metricUnits: {
          load1: {
            notation: 'decimal',
            symbol: '',
            precision: { type: 'strict', digits: 2 },
            scale: 1
          }
        }
      }
    })
    // The exact-match query pins the readout to "1.09"; no "%" may show anywhere.
    expect(screen.getByText('1.09')).toBeInTheDocument()
    expect(screen.queryByText(/%/)).toBeNull()
  })

  // A genuine % unit still reads as a percent — the value already carries it.
  it('keeps the percent for a real % metric', () => {
    render(GadgetRenderer, {
      props: {
        type: 'gauge',
        metric: 'util',
        state: makeState({ perf_data: 'util=8.54%;;;0;100', state: 'OK' }),
        size: 120,
        metricUnits: {
          util: {
            notation: 'decimal',
            symbol: '%',
            precision: { type: 'auto', digits: 2 },
            scale: 1
          }
        }
      }
    })
    expect(screen.getByText('8.54%')).toBeInTheDocument()
  })
})

describe('GadgetRenderer existing gadgets', () => {
  it.each([
    ['trafficlight', '.maps-gadget-renderer__traffic'],
    ['bar', '.maps-gadget-renderer__track'],
    ['gauge', 'svg']
  ])('still renders the %s branch', (type, selector) => {
    const { container } = render(GadgetRenderer, {
      props: { type, state: makeState(), size: 60 }
    })
    // The gadget bodies are purely visual (coloured bulbs/bars/arcs with no
    // text or ARIA surface — the traffic light renders no text at all), so
    // branch selection is only observable structurally.
    expect(container.querySelector(selector)).not.toBeNull()
    expect(container.querySelector('.maps-gadget-renderer__raw')).toBeNull()
  })
})
