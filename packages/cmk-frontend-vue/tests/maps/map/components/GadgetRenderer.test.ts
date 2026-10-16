/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import GadgetRenderer from '@/maps/map/components/GadgetRenderer.vue'
import type { MetricUnitMap, ObjectState, PerfometerResult } from '@/maps/types/api'

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

describe('GadgetRenderer unconfigured metric', () => {
  // CPU load lists load15 first, but its Perf-O-Meter reads load1; a gadget
  // without a configured metric must show what its caption shows.
  it.each(['gauge', 'bar', 'value'])('shows the Perf-O-Meter reading on a %s', (type) => {
    render(GadgetRenderer, {
      props: {
        type,
        state: makeState({ perf_data: 'load15=6.79;60;120;; load1=3.63;;;0;12' }),
        size: 120,
        perfometer: {
          label: '3.63',
          rows: [],
          sides: [{ title: null, label: '3.63', pct: 51.42 }],
          bg_color: '#000'
        }
      }
    })

    expect(screen.queryByText('6.79')).toBeNull()
    expect(screen.getByText('3.63')).toBeInTheDocument()
  })
})

describe('GadgetRenderer two-sided Perf-O-Meter', () => {
  function renderSides(sides: PerfometerResult['sides']) {
    return render(GadgetRenderer, {
      props: {
        type: 'bar',
        state: makeState({ perf_data: 'if_in_bps=244;;;; if_out_bps=131;;;;' }),
        size: 120,
        perfometer: { label: '244 bit/s / 131 bit/s', rows: [], sides, bg_color: '#000' }
      }
    })
  }
  const fill = (container: Element) =>
    container.querySelector<HTMLElement>('.maps-gadget-renderer__fill')?.style.width

  it('shows the side it fills and names both in the caption', () => {
    const { container } = renderSides([
      { title: 'In', label: '244 bit/s', pct: 60 },
      { title: 'Out', label: '131 bit/s', pct: 30 }
    ])

    expect(screen.getByText('244 bit/s')).toBeInTheDocument()
    expect(screen.getByText('In / Out')).toBeInTheDocument()
    expect(screen.getByText('244 bit/s / 131 bit/s')).toBeInTheDocument()
    expect(fill(container)).toBe('60%')
  })

  it('fills from the first side that is drawn', () => {
    const { container } = renderSides([null, { title: 'Out', label: '131 bit/s', pct: 30 }])

    expect(screen.getByText('131 bit/s')).toBeInTheDocument()
    expect(fill(container)).toBe('30%')
  })
})

describe('GadgetRenderer caption', () => {
  const perfometer: PerfometerResult = {
    label: '48.91 %',
    rows: [],
    sides: [{ title: 'RAM usage', label: '48.91 %', pct: 48.91 }],
    bg_color: '#000'
  }

  // A gadget is narrower than "RAM usage 48.91 %"; on its own line the value
  // survives when the title has to be shortened.
  it.each(['bar', 'gauge'])('puts the %s value on a line of its own', (type) => {
    render(GadgetRenderer, {
      props: {
        type,
        metric: 'mem_used',
        state: makeState(),
        size: 60,
        perfometer,
        metricUnits: units
      }
    })

    expect(screen.getByText('RAM usage')).toBeInTheDocument()
    expect(screen.getByText('48.91 %')).toBeInTheDocument()
  })

  it.each(['bar', 'gauge'])('leaves out a %s value the readout already shows', (type) => {
    render(GadgetRenderer, { props: { type, state: makeState(), size: 60, perfometer } })

    expect(screen.getByText('RAM usage')).toBeInTheDocument()
    expect(screen.getAllByText('48.91 %')).toHaveLength(1)
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
