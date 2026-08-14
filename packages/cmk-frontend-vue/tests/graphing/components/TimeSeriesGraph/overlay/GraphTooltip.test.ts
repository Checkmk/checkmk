/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import type {
  HoverSample,
  HoverState
} from '@/graphing/components/TimeSeriesGraph/interaction/hover'
import GraphTooltip from '@/graphing/components/TimeSeriesGraph/overlay/GraphTooltip.vue'

function makeSample(overrides: Partial<HoverSample>): HoverSample {
  return {
    metricName: 'cpu',
    label: 'CPU',
    color: '#ff0000',
    formattedValue: '42 %',
    attributes: [],
    pixelY: 10,
    snapTime: 1000,
    isClosest: false,
    ...overrides
  }
}

const BACKEND_ATTRIBUTES: HoverSample['attributes'] = [
  { kind: 'resource', name: 'host.arch', value: 'x64' },
  { kind: 'data_point', name: 'status', value: '304' }
]

function makeHoverState(overrides: Partial<HoverState>): HoverState {
  return {
    cursorX: 5,
    cursorY: 5,
    clientX: 105,
    clientY: 205,
    snapX: 5,
    snapTime: 1000,
    samples: [makeSample({})],
    ...overrides
  }
}

function renderGraphTooltip(hoverState: HoverState | null): ReturnType<typeof render> {
  return render(GraphTooltip, { props: { hoverState } })
}

describe('GraphTooltip', () => {
  test('renders one sample per metric with label and formatted value', () => {
    renderGraphTooltip(
      makeHoverState({
        samples: [
          makeSample({ metricName: 'cpu', label: 'CPU', formattedValue: '42 %' }),
          makeSample({ metricName: 'mem', label: 'Memory', formattedValue: '1.5 GB' })
        ]
      })
    )

    expect(screen.getByText('CPU')).toBeInTheDocument()
    expect(screen.getByText('42 %')).toBeInTheDocument()
    expect(screen.getByText('Memory')).toBeInTheDocument()
    expect(screen.getByText('1.5 GB')).toBeInTheDocument()
  })

  test('marks only the closest sample with the emphasis class', () => {
    renderGraphTooltip(
      makeHoverState({
        samples: [
          makeSample({ metricName: 'cpu', label: 'CPU', isClosest: false }),
          makeSample({ metricName: 'mem', label: 'Memory', isClosest: true })
        ]
      })
    )

    const emphasized = document.querySelectorAll('.graphing-graph-tooltip__row--is-closest')
    expect(emphasized).toHaveLength(1)
    expect(emphasized[0]!.textContent).toContain('Memory')
  })

  test('shows the snap time as weekday, ISO date and 24h clock time', () => {
    renderGraphTooltip(makeHoverState({ snapTime: 1781526896 }))

    expect(screen.getByText(/, \d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/)).toBeInTheDocument()
  })

  test('positions the tooltip beside the viewport cursor coordinates', () => {
    renderGraphTooltip(makeHoverState({ clientX: 105, clientY: 205 }))

    const tooltip = document.querySelector<HTMLElement>('.graphing-graph-tooltip')
    // jsdom reports a zero-size element, so the position degrades to cursor + offset;
    // flip and clamp behaviour is covered by the computeTooltipPosition unit tests.
    expect(tooltip!.style.left).toBe('121px')
    expect(tooltip!.style.top).toBe('205px')
  })

  test('keeps the scoped-style attribute when teleported to the body', () => {
    renderGraphTooltip(makeHoverState({}))

    const tooltip = document.querySelector<HTMLElement>('.graphing-graph-tooltip')
    expect(tooltip!.parentElement).toBe(document.body)
    // Without the scope attribute none of the component's styles would match — the
    // exact regression the previous reka-ui portal shipped with.
    const attributeNames = Array.from(tooltip!.attributes).map((attribute) => attribute.name)
    expect(attributeNames.some((name) => name.startsWith('data-v-'))).toBe(true)
  })

  test("lists the hovered line's attributes grouped by kind", () => {
    renderGraphTooltip(
      makeHoverState({
        samples: [makeSample({ isClosest: true, attributes: BACKEND_ATTRIBUTES })]
      })
    )

    expect(screen.getByText('Resource attributes')).toBeInTheDocument()
    expect(screen.getByText('host.arch')).toBeInTheDocument()
    expect(screen.getByText('x64')).toBeInTheDocument()
    expect(screen.getByText('Data point attributes')).toBeInTheDocument()
    expect(screen.getByText('status')).toBeInTheDocument()
    expect(screen.getByText('304')).toBeInTheDocument()
    expect(screen.queryByText('Scope attributes')).not.toBeInTheDocument()
  })

  test('lists the attributes of the hovered line only, not of every line under the cursor', () => {
    renderGraphTooltip(
      makeHoverState({
        samples: [
          makeSample({ metricName: 'cpu', label: 'CPU', isClosest: true, attributes: [] }),
          makeSample({
            metricName: 'mem',
            label: 'Memory',
            isClosest: false,
            attributes: BACKEND_ATTRIBUTES
          })
        ]
      })
    )

    expect(screen.getByText('Memory')).toBeInTheDocument()
    expect(screen.queryByText('host.arch')).not.toBeInTheDocument()
  })

  test('an RRD line adds no attribute block at all', () => {
    renderGraphTooltip(
      makeHoverState({ samples: [makeSample({ isClosest: true, attributes: [] })] })
    )

    expect(document.querySelector('.graphing-graph-tooltip__attributes')).toBeNull()
  })

  test('renders nothing without a hover state', () => {
    renderGraphTooltip(null)

    expect(document.querySelector('.graphing-graph-tooltip')).toBeNull()
  })
})
