/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapLine from '@/maps/map/static/components/MapLine.vue'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aState, anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// NOTE: MapLine draws pure SVG geometry (gradients, polylines, arrow
// polygons, drag handles) with no accessible representation, so every
// assertion in this file is a targeted DOM query scoped to the render
// container.

function makeLineObject(overrides: Partial<MapElement> = {}): MapElement {
  return anObject({
    id: 'line_1',
    type: 'line',
    x: 100,
    y: 100,
    x2: 250,
    y2: 100,
    line_style: 'plain',
    label: { show: false, x: 0, y: 0, size: 10, color: '#fff', background: 'transparent' },
    url_target: '_blank',
    z: 1,
    ...overrides
  })
}

const noState: ObjectState = aState({
  object_id: 'line_1',
  type: 'host',
  state: 'UP',
  output: '',
  perf_data: '',
  acknowledged: false,
  in_downtime: false,
  stale: false
})

function renderLine(object: MapElement, editMode = false): Element {
  const { container } = render(MapLine, {
    global: mapsGlobal(),
    props: { object, state: noState, editMode }
  })
  return container
}

// A weather-coloured line is the orthogonal `line_weather_color: true` flag,
// independent of the chosen shape. The directional in→out gradient only
// renders when a *second* outbound metric is configured — with only one
// metric, the line uses a solid color.
const weatherProps = {
  line_style: 'arrow_inward' as const,
  line_weather_color: true,
  host_name: 'h',
  service_description: 's',
  weathermap_metric: 'in',
  weathermap_metric_out: 'out'
}

describe('MapLine – weather-color gradient', () => {
  it('renders a <defs> linearGradient when both in/out metrics are configured', () => {
    const container = renderLine(makeLineObject(weatherProps))
    expect(container.querySelector('defs')).not.toBeNull()
    expect(container.querySelector('linearGradient')).not.toBeNull()
  })

  it('uses gradientUnits="userSpaceOnUse" (not objectBoundingBox)', () => {
    const container = renderLine(makeLineObject(weatherProps))
    const grad = container.querySelector('linearGradient')
    expect(grad?.getAttribute('gradientUnits')).toBe('userSpaceOnUse')
  })

  it('binds gradient x1/y1/x2/y2 to line start/end coordinates', () => {
    const container = renderLine(
      makeLineObject({ ...weatherProps, x: 50, y: 80, x2: 300, y2: 200 })
    )
    const grad = container.querySelector('linearGradient')
    expect(grad?.getAttribute('x1')).toBe('50')
    expect(grad?.getAttribute('y1')).toBe('80')
    expect(grad?.getAttribute('x2')).toBe('300')
    expect(grad?.getAttribute('y2')).toBe('200')
  })

  it('gradient id matches the stroke url() reference', () => {
    const container = renderLine(makeLineObject(weatherProps))
    const gradId = container.querySelector('linearGradient')?.getAttribute('id')
    expect(gradId).toBeDefined()
    const lineStroke = [...container.querySelectorAll('line')].find((l) =>
      l.getAttribute('stroke')?.startsWith('url(')
    )
    expect(lineStroke).toBeDefined()
    expect(lineStroke!.getAttribute('stroke')).toBe(`url(#${gradId})`)
  })

  it('does not render a <defs> for non-weather-coloured lines', () => {
    const container = renderLine(makeLineObject({ line_style: 'plain' }))
    expect(container.querySelector('defs')).toBeNull()
  })

  it('falls back to a solid stroke when only the inbound metric is set', () => {
    const container = renderLine(
      makeLineObject({
        line_style: 'arrow_inward',
        line_weather_color: true,
        host_name: 'h',
        service_description: 's',
        weathermap_metric: 'in'
      })
    )
    expect(container.querySelector('linearGradient')).toBeNull()
    const stroked = [...container.querySelectorAll('line')].find((l) =>
      l.getAttribute('stroke')?.startsWith('url(')
    )
    expect(stroked).toBeUndefined()
  })
})

describe('MapLine – styling regressions', () => {
  it('plain lines do not render a dot at the endpoint', () => {
    const container = renderLine(makeLineObject({ line_style: 'plain' }))
    // Only the invisible hit-area + the visible stroke are expected; no
    // decorative <circle> at the endpoint.
    expect(container.querySelectorAll('circle')).toHaveLength(0)
  })

  it('dashed line scales stroke-dasharray with line_width', () => {
    const thin = renderLine(makeLineObject({ line_style: 'dashed', line_width: 2 }))
    const thick = renderLine(makeLineObject({ line_style: 'dashed', line_width: 15 }))
    const lastDash = (c: Element) =>
      [...c.querySelectorAll('polyline')].at(-1)!.getAttribute('stroke-dasharray')
    const thinDash = lastDash(thin)
    const thickDash = lastDash(thick)
    expect(thinDash).not.toBeNull()
    expect(thickDash).not.toBeNull()
    // First number of "<gap> <dash>"
    const thinFirst = parseFloat(thinDash!.split(' ')[0] ?? '')
    const thickFirst = parseFloat(thickDash!.split(' ')[0] ?? '')
    expect(thickFirst).toBeGreaterThan(thinFirst)
  })

  it('arrow_end shortens the stroke so the cap sits behind the arrow tip', () => {
    const container = renderLine(
      makeLineObject({
        line_style: 'arrow_end',
        line_width: 15,
        x: 0,
        y: 0,
        x2: 200,
        y2: 0
      })
    )
    // The visible stroke is a <polyline>; its last point is the end.
    const visibleLine = [...container.querySelectorAll('polyline')].at(-1)!
    const pts = visibleLine.getAttribute('points')!.trim().split(/\s+/)
    const x2 = parseFloat(pts.at(-1)?.split(',')[0] ?? '')
    // Stroke must end before the arrow tip (x=200).
    expect(x2).toBeLessThan(200)
    // Arrow polygon's first vertex is the tip — should still anchor at x=200.
    const polygon = container.querySelector('polygon')
    expect(polygon).not.toBeNull()
    const tip = polygon!.getAttribute('points')!.split(' ')[0] ?? ''
    expect(parseFloat(tip.split(',')[0] ?? '')).toBe(200)
  })

  it('arrow_inward (middle) arrows scale with line_width', () => {
    const thin = renderLine(makeLineObject({ line_style: 'arrow_inward', line_width: 2 }))
    const thick = renderLine(makeLineObject({ line_style: 'arrow_inward', line_width: 15 }))
    // Both render the two midpoint triangles.
    expect(thin.querySelectorAll('polygon').length).toBeGreaterThanOrEqual(2)
    expect(thick.querySelectorAll('polygon').length).toBeGreaterThanOrEqual(2)
    // The right triangle's points string encodes a base offset perpendicular
    // to the line — at width=15 the triangle is geometrically larger.
    // length ≥ 2 asserted above
    const thinPoly = thin.querySelectorAll('polygon')[0]!.getAttribute('points')!
    const thickPoly = thick.querySelectorAll('polygon')[0]!.getAttribute('points')!
    // Compare the spread between the three vertices' x coordinates.
    const xs = (s: string) => s.split(' ').map((p) => parseFloat(p.split(',')[0] ?? ''))
    const span = (s: string) => Math.max(...xs(s)) - Math.min(...xs(s))
    expect(span(thickPoly)).toBeGreaterThan(span(thinPoly))
  })
})

describe('MapLine – bend (explicit midpoint)', () => {
  it('routes the stroke through the bend point when mid_x/mid_y are set', () => {
    const container = renderLine(
      makeLineObject({ x: 0, y: 0, x2: 200, y2: 0, mid_x: 100, mid_y: 80 })
    )
    const fill = [...container.querySelectorAll('polyline')].at(-1)!
    const pts = fill.getAttribute('points')!.trim().split(/\s+/)
    // start, bend, end — the bend is the middle vertex.
    expect(pts).toHaveLength(3)
    expect(pts[1]).toBe('100,80')
  })

  it('keeps a straight two-point stroke when no bend is set', () => {
    const container = renderLine(makeLineObject({ x: 0, y: 0, x2: 200, y2: 0 }))
    const fill = [...container.querySelectorAll('polyline')].at(-1)!
    expect(fill.getAttribute('points')!.trim().split(/\s+/)).toHaveLength(2)
  })

  it('shows three drag handles in edit mode (start, end, bend)', () => {
    const container = renderLine(makeLineObject(), true)
    expect(container.querySelectorAll('circle')).toHaveLength(3)
  })
})
