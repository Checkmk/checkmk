/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Drawing the ring around a map object's icon.
 *
 * Plain D3 on a dedicated overlay SVG the component hands over: D3 owns every
 * node inside it, so nothing here fights Vue over the DOM. The reactive side —
 * when to draw, with which colours — is ``useArcRing``.
 */
import { easeBackOut, easeCubicOut, easeQuadInOut } from 'd3-ease'
import { interpolate } from 'd3-interpolate'
import { type Selection, select } from 'd3-selection'
import { arc } from 'd3-shape'
import { transition } from 'd3-transition'

// Importing d3-transition for its side effect is what puts .transition() on a
// selection; the void keeps the import from looking unused.
void transition

/** 12 o'clock — where a utilisation arc starts and a full ring closes. */
const START_ANGLE = -Math.PI / 2

/** Gap between the icon's edge and the ring. */
export const RING_PAD = 6

export interface RingColors {
  /** The object's state colour, used by the state ring and the pulse. */
  state: string
  /** The filled part of a utilisation arc. */
  fill: string
  /** The unfilled remainder of a utilisation arc. */
  track: string
}

interface RingGeometry {
  size: number
  outerRadius: number
  innerRadius: number
}

function geometryOf(iconSize: number): RingGeometry {
  const outerRadius = iconSize / 2 + RING_PAD
  return {
    size: iconSize + RING_PAD * 2,
    outerRadius,
    innerRadius: outerRadius - Math.max(3, iconSize * 0.07)
  }
}

/** The group D3 owns, created (and popped in) on first draw. */
function ringGroup(
  svg: SVGSVGElement,
  geometry: RingGeometry
): Selection<SVGGElement, unknown, null, undefined> {
  const root = select(svg)
  root.attr('width', geometry.size).attr('height', geometry.size)
  const centre = `translate(${geometry.size / 2},${geometry.size / 2})`
  const existing = root.select<SVGGElement>('g.arc-root')
  if (!existing.empty()) {
    return existing
  }
  // pointer-events explicitly on the group, so every node D3 appends is
  // guaranteed non-interactive whatever a browser infers for SVG.
  const group = root
    .append('g')
    .attr('class', 'arc-root')
    .attr('pointer-events', 'none')
    .attr('transform', `${centre} scale(0.6)`)
    .attr('opacity', '0')
  group
    .transition()
    .duration(300)
    .ease(easeBackOut.overshoot(1.4))
    .attr('transform', `${centre} scale(1)`)
    .attr('opacity', '1')
  return group
}

/**
 * Draw the ring: a plain state ring when the object has no utilisation to
 * report, otherwise a track with the utilisation arc animating onto it.
 */
export function drawRing(
  svg: SVGSVGElement,
  iconSize: number,
  pct: number | null,
  colors: RingColors
): void {
  const geometry = geometryOf(iconSize)
  const group = ringGroup(svg, geometry)
  const arcGen = arc()
  const radii = { innerRadius: geometry.innerRadius, outerRadius: geometry.outerRadius }

  if (pct === null) {
    group.select('path.arc-track').remove()
    group.select('path.arc-fg').remove()
    const ring = group.select<SVGPathElement>('path.state-ring')
    const target = ring.empty() ? group.append('path').attr('class', 'state-ring') : ring
    target
      .attr('d', arcGen({ ...radii, startAngle: -Math.PI, endAngle: Math.PI })!)
      .style('fill', colors.state)
      .attr('opacity', '0.35')
    return
  }

  group.select('path.state-ring').remove()

  const track = group.select<SVGPathElement>('path.arc-track')
  const trackTarget = track.empty() ? group.append('path').attr('class', 'arc-track') : track
  trackTarget
    .attr('d', arcGen({ ...radii, startAngle: START_ANGLE, endAngle: START_ANGLE + 2 * Math.PI })!)
    .style('fill', colors.track)

  // The reached angle is parked on the node so a new target animates from
  // wherever the previous transition actually got to, not from zero.
  type ArcPath = SVGPathElement & { _currentEndAngle?: number }
  let foreground = group.select<ArcPath>('path.arc-fg')
  if (foreground.empty()) {
    foreground = group.append('path').attr('class', 'arc-fg')
    foreground.attr('d', arcGen({ ...radii, startAngle: START_ANGLE, endAngle: START_ANGLE })!)
    foreground.node()!._currentEndAngle = START_ANGLE
  }
  const node = foreground.node()!
  const fromAngle = node._currentEndAngle ?? START_ANGLE
  const toAngle = START_ANGLE + (pct / 100) * 2 * Math.PI
  foreground.style('fill', colors.fill)
  foreground
    .transition()
    .duration(600)
    .ease(easeQuadInOut)
    .attrTween('d', () => {
      const interpolateAngle = interpolate(fromAngle, toAngle)
      return (progress: number) => {
        const angle = interpolateAngle(progress)
        node._currentEndAngle = angle
        return arcGen({ ...radii, startAngle: START_ANGLE, endAngle: angle })!
      }
    })
}

/** Stop and remove the attention pulse, if one is running. */
export function clearPulse(svg: SVGSVGElement): void {
  select(svg).select('circle.pulse-ring').interrupt().remove()
}

/** A circle expanding out of the ring on repeat, for states worth noticing. */
export function startPulse(svg: SVGSVGElement, iconSize: number, color: string): void {
  const geometry = geometryOf(iconSize)
  const group = select(svg).select<SVGGElement>('g.arc-root')
  if (group.empty()) {
    return
  }
  clearPulse(svg)
  const pulse = group
    .append('circle')
    .attr('class', 'pulse-ring')
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('fill', 'none')
    .attr('stroke-width', '1.5')
    .style('stroke', color)

  function step(): void {
    pulse
      .attr('r', String(geometry.innerRadius))
      .attr('opacity', '0.7')
      .transition()
      .duration(900)
      .ease(easeCubicOut)
      .attr('r', String(geometry.outerRadius + 8))
      .attr('opacity', '0')
      .on('end', step)
  }
  step()
}
