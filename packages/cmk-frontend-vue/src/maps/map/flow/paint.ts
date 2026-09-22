/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a flow map's nodes and edges look like.
 *
 * Drawing only — no state, no events, no lifecycle. The canvas owns the d3 data
 * joins and decides what a click means; these functions are handed the
 * resulting selections and paint them.
 *
 * The split matters at scale. Entering a node builds its shape once; everything
 * that can change afterwards is written on the merged selection, and the three
 * things that depend on the zoom are written again when a gesture settles. The
 * per-frame tick writes nothing but positions: fills and strokes only change on
 * a topology push, and rewriting them every frame would be thousands of style
 * writes per frame on a few hundred hosts.
 *
 * Colours go through ``style``, not through a presentation attribute, because
 * only the former resolves ``var()`` — that is what keeps the state colours on
 * the shared tokens and following the operator's theme.
 */
import type { Selection } from 'd3-selection'
import { select } from 'd3-selection'

import { stateColorVar } from '@/maps/utils/stateColors'

import {
  DONUT_MAX_WIDTH,
  type DonutArc,
  type DonutSegment,
  NODE_R,
  buildDonutArc,
  donutOuterRadius,
  donutPie,
  finiteOr,
  showSvcLabel,
  svcR
} from './geometry'
import { rowSpacingFallback, siteScaleForZoom } from './layout'
import { serviceNameOf } from './nodeIds'
import type { CmdMarker, FLink, FNode } from './nodes'

/**
 * The classes the drawn parts carry. Shared, because the search, the selection
 * and the stylesheet all reach for the same elements the painter makes.
 */
export const flowClass = {
  zoomLayer: 'maps-flow-canvas__zoom-layer',
  links: 'maps-flow-canvas__links',
  nodes: 'maps-flow-canvas__nodes',
  link: 'maps-flow-canvas__link',
  serviceLink: 'maps-flow-canvas__link--service',
  node: 'maps-flow-canvas__node',
  donut: 'maps-flow-canvas__donut',
  glyph: 'maps-flow-canvas__glyph',
  label: 'maps-flow-canvas__label',
  badges: 'maps-flow-canvas__badges',
  badge: 'maps-flow-canvas__badge'
} as const

/** A node kind as a class modifier, so the stylesheet can single one out. */
export function nodeKindClass(node: FNode): string {
  return `${flowClass.node} ${flowClass.node}--${node.nodeType}`
}

export type NodeSelection = Selection<SVGGElement, FNode, SVGGElement, unknown>
export type LinkSelection = Selection<SVGLineElement, FLink, SVGGElement, unknown>

/** What the stylesheet reads a host's halo from — see ``FlowCanvas``. */
const HALO_COLOR_PROPERTY = '--maps-flow-canvas-halo'
const HALO_WIDTH_PROPERTY = '--maps-flow-canvas-halo-width'
/** A site link carries no state of its own, so it takes the muted text colour. */
const SITE_LINK_COLOR = 'var(--font-color-dimmed)'
const GLYPH_COLOR = 'rgb(255 255 255 / 90%)'
const MORE_GLYPH_COLOR = 'rgb(255 255 255 / 95%)'

const SITE_WIDTH = 110
const SITE_HEIGHT = 36

/** Everything about a node that a topology push can change. */
export interface NodeVisuals {
  /** The current zoom, which the donut width and the host labels track. */
  scale: number
  /** Whether the donut ring is on show for this host at all. */
  showsDonut: (node: FNode) => boolean
  /** Id of the filter that lifts the worst-affected hosts out of the map. */
  glowFilter: string
  isWorst: (node: FNode) => boolean
  halo: (node: FNode) => { stroke: string; width: number }
  donutSegments: (node: FNode) => DonutSegment[]
  badges: (node: FNode) => CmdMarker[]
  ariaLabel: (node: FNode) => string
  /** What the label under a "+N more" stand-in reads, translated. */
  moreLabel: (count: number) => string
}

const isKind =
  (...kinds: FNode['nodeType'][]) =>
  (node: FNode): boolean =>
    kinds.includes(node.nodeType)

/** Builds the shape of each newly entered node, by kind. */
export function drawNodes(enter: NodeSelection): void {
  drawSiteNode(enter.filter(isKind('site')))
  drawHostNode(enter.filter(isKind('host')))
  drawServiceNode(enter.filter(isKind('service')))
  drawMoreNode(enter.filter(isKind('more')))
  // The command badges are appended last, so they sit over the node they
  // describe. They never take the pointer: the hover card carries the same
  // information in words, and stealing a drag to show a badge would be worse.
  enter
    .filter(isKind('host', 'service'))
    .append('g')
    .attr('class', flowClass.badges)
    .attr('pointer-events', 'none')
}

/** A site root: a rounded box with the site's name in it. */
function drawSiteNode(enter: NodeSelection): void {
  enter
    .append('rect')
    .attr('x', -SITE_WIDTH / 2)
    .attr('y', -SITE_HEIGHT / 2)
    .attr('width', SITE_WIDTH)
    .attr('height', SITE_HEIGHT)
    .attr('rx', 8)
    .style('fill', 'var(--ux-theme-3)')
    .style('stroke', 'var(--font-color-dimmed)')
    .style('stroke-width', 1.5)
  enter
    .append('text')
    .attr('class', flowClass.glyph)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', 9)
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.08em')
    .attr('pointer-events', 'none')
    .attr('y', -8)
    .style('fill', 'var(--font-color-dimmed)')
    .text('SITE')
  enter
    .append('text')
    .attr('class', flowClass.label)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', 13)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .attr('y', 6)
    .style('fill', 'var(--font-color)')
}

function drawHostNode(enter: NodeSelection): void {
  // The stroke is the stylesheet's: it has to give way to the selection ring.
  enter.append('circle').attr('r', NODE_R)
  // Empty for now — the ring's segments are bound on every refresh.
  enter.append('g').attr('class', flowClass.donut).attr('pointer-events', 'none')
  enter
    .append('text')
    .attr('class', flowClass.glyph)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', 11)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .style('fill', GLYPH_COLOR)
    .text('H')
  enter
    .append('text')
    .attr('class', flowClass.label)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 11)
    .attr('font-weight', '500')
    .attr('pointer-events', 'none')
    // Refined against the current zoom by ``refreshHostLabels``; the widest
    // possible offset keeps the very first paint clear of the ring.
    .attr('y', NODE_R + DONUT_MAX_WIDTH + 5)
    .style('fill', 'var(--font-color)')
}

/**
 * The glyph in the middle of a service-like dot: what tells a service apart
 * from a "+N more" stand-in. Only the colour can be written on entry -- the
 * text and its size follow the host's service count, which a push can change.
 */
interface GlyphSpec {
  text: (node: FNode) => string
  size: (node: FNode) => number
  color: string
}

const SERVICE_GLYPH: GlyphSpec = {
  text: () => 'S',
  size: (node) => (svcR(node.svcTotalCount ?? 1) <= 7 ? 6 : 8),
  color: GLYPH_COLOR
}

const MORE_GLYPH: GlyphSpec = {
  text: (node) => `+${node.moreCount ?? 0}`,
  size: (node) => (svcR(node.svcTotalCount ?? 1) <= 7 ? 7 : 9),
  color: MORE_GLYPH_COLOR
}

/**
 * A service and a "+N more" stand-in share a shape — a circle, a glyph in the
 * middle, a label below — and differ only in what the glyph reads. What their
 * size follows from is left to ``refreshServiceLikeNodes``, which runs on the
 * merged selection right after this.
 */
function drawServiceLikeNode(enter: NodeSelection, glyph: GlyphSpec): void {
  // The stroke is the stylesheet's, as for a host: it has to give way to the
  // selection ring, which an inline style would beat.
  enter.append('circle')
  enter
    .append('text')
    .attr('class', flowClass.glyph)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .style('fill', glyph.color)
  enter
    .append('text')
    .attr('class', flowClass.label)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 9)
    .attr('font-weight', '400')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--font-color)')
}

function drawServiceNode(enter: NodeSelection): void {
  drawServiceLikeNode(enter, SERVICE_GLYPH)
}

function drawMoreNode(enter: NodeSelection): void {
  drawServiceLikeNode(enter, MORE_GLYPH)
}

/**
 * Everything a service-like dot takes from its host's service count. The layout
 * re-derives the ring's spacing from that same count on every push, so a dot
 * left at an older radius would overlap its neighbours and sit on its own label.
 */
function refreshServiceLikeNodes(merge: NodeSelection): void {
  const svcLike = merge.filter(isKind('service', 'more'))
  svcLike.select('circle').attr('r', (node) => svcR(node.svcTotalCount ?? 1))
  svcLike
    .select(`text.${flowClass.label}`)
    .attr('y', (node) => svcR(node.svcTotalCount ?? 1) + 4)
    // A service label only fits while there are few enough of them, and which
    // that is changes with the layout.
    .style('display', (node) => (showSvcLabel(node.svcTotalCount ?? 1) ? null : 'none'))
  merge
    .filter(isKind('service'))
    .select(`text.${flowClass.glyph}`)
    .attr('font-size', SERVICE_GLYPH.size)
    .text(SERVICE_GLYPH.text)
  merge
    .filter(isKind('more'))
    .select(`text.${flowClass.glyph}`)
    .attr('font-size', MORE_GLYPH.size)
    .text(MORE_GLYPH.text)
}

/**
 * How an edge is drawn. Everything but the colour is decided by what the edge
 * connects, which cannot change while the edge exists — the data join is keyed
 * on both ends — so it is written once here, on entry.
 */
export function drawLinks(enter: LinkSelection): void {
  enter
    .attr('class', (link) =>
      link.isServiceLink ? `${flowClass.link} ${flowClass.serviceLink}` : flowClass.link
    )
    .attr('stroke-opacity', (link) => {
      if (isFromSite(link)) {
        return 0.55
      }
      return link.isServiceLink ? 0.3 : 0.45
    })
    .attr('stroke-width', (link) => {
      if (isFromSite(link)) {
        return 1
      }
      return link.isServiceLink ? 1 : 1.5
    })
    .attr('stroke-dasharray', (link) => {
      if (isFromSite(link)) {
        return '2,3'
      }
      return link.isServiceLink ? '3,3' : null
    })
}

/** The one thing about an edge that a topology push can have changed. */
export function refreshLinks(merge: LinkSelection): void {
  merge.style('stroke', (link) =>
    isFromSite(link) ? SITE_LINK_COLOR : stateColorVar(link.source.state)
  )
}

/** Writes everything a topology push can have changed about the nodes. */
export function refreshNodes(merge: NodeSelection, visuals: NodeVisuals): void {
  // The accessible name follows the live state, so it is rewritten every time.
  merge.attr('aria-label', visuals.ariaLabel)
  merge.select('circle').style('fill', (node) => stateColorVar(node.state))
  merge.select(`text.${flowClass.label}`).text((node) => labelOf(node, visuals.moreLabel))
  refreshServiceLikeNodes(merge)

  const hosts = merge.filter(isKind('host'))
  hosts.each(function (node) {
    const group = this as SVGGElement
    // The halo goes onto the group as two custom properties rather than onto
    // the circle as a style, so the stylesheet can let a selection ring win
    // over it — an inline style on the circle would beat any rule.
    const halo = visuals.halo(node)
    group.style.setProperty(HALO_COLOR_PROPERTY, halo.stroke)
    group.style.setProperty(HALO_WIDTH_PROPERTY, String(halo.width))
    // The glow hangs on the group too, so the worst hosts stay unmissable even
    // fitted to screen, where a stroke width collapses to under a screen pixel.
    if (visuals.isWorst(node)) {
      group.setAttribute('filter', `url(#${visuals.glowFilter})`)
    } else {
      group.removeAttribute('filter')
    }
  })
  refreshDonuts(hosts, visuals)
  refreshBadges(merge.filter(isKind('host', 'service')), visuals.badges)
}

/**
 * Binds each host's aggregated service states as proportional arcs. Which hosts
 * get a ring is the caller's rule; ``exit`` clears the paths of a host that
 * has just stopped qualifying.
 */
function refreshDonuts(hosts: NodeSelection, visuals: NodeVisuals): void {
  const arc = buildDonutArc(visuals.scale)
  hosts.each(function (node) {
    const arcs = donutPie(visuals.showsDonut(node) ? visuals.donutSegments(node) : [])
    const group = (this as SVGGElement).querySelector<SVGGElement>(`g.${flowClass.donut}`)
    if (!group || (arcs.length === 0 && group.childElementCount === 0)) {
      // Nothing to draw and nothing left over: the join would only allocate.
      return
    }
    const paths = select(group)
      .selectAll<SVGPathElement, (typeof arcs)[number]>('path')
      .data(arcs, (slice) => slice.data.state)
    paths.exit().remove()
    paths
      .enter()
      .append('path')
      .merge(paths)
      .attr('d', (slice) => arc(slice) ?? '')
      .style('fill', (slice) => stateColorVar(slice.data.state))
      .style('stroke', 'rgb(0 0 0 / 35%)')
      .style('stroke-width', 0.5)
  })
}

/** Binds the acknowledged / in-downtime / notifications-off corner badges. */
function refreshBadges(merge: NodeSelection, badges: (node: FNode) => CmdMarker[]): void {
  merge.each(function (node) {
    const markers = badges(node)
    const group = (this as SVGGElement).querySelector<SVGGElement>(`g.${flowClass.badges}`)
    if (!group || (markers.length === 0 && group.childElementCount === 0)) {
      // The common case by far: no command is in force on this node.
      return
    }
    const radius = node.nodeType === 'service' ? svcR(node.svcTotalCount ?? 1) : NODE_R
    const badgeR = Math.max(4, radius * 0.34)
    const bound = select(group)
      .selectAll<SVGGElement, CmdMarker>(`g.${flowClass.badge}`)
      .data(markers, (marker) => marker.key)
    bound.exit().remove()
    const entered = bound.enter().append('g').attr('class', flowClass.badge)
    entered.append('circle').style('stroke', 'var(--ux-theme-3)').style('stroke-width', 1.5)
    entered
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-weight', '700')
    entered.append('title')
    const all = entered.merge(bound)
    all.attr('transform', (marker) => {
      const [x, y] = badgeOffset(marker.corner, radius)
      return `translate(${x},${y})`
    })
    all
      .select('circle')
      .attr('r', badgeR)
      .style('fill', (marker) => marker.fill)
    all
      .select('text')
      .attr('font-size', badgeR * 1.3)
      .style('fill', (marker) => marker.fg)
      .text((marker) => marker.glyph)
    all.select('title').text((marker) => marker.title)
  })
}

function badgeOffset(corner: CmdMarker['corner'], radius: number): [number, number] {
  const offset = radius * 0.72
  if (corner === 'tr') {
    return [offset, -offset]
  }
  if (corner === 'tl') {
    return [-offset, -offset]
  }
  return [offset, offset]
}

/**
 * Redraws the donut rings at a new zoom, without rebinding their data. Queried
 * from the drawing area rather than per node: ``selectAll`` on a selection of a
 * few thousand groups is a few thousand DOM queries.
 */
export function refreshDonutWidths(area: SVGSVGElement, scale: number): void {
  const arc = buildDonutArc(scale)
  select(area)
    .selectAll<SVGPathElement, DonutArc>(`g.${flowClass.donut} path`)
    .attr('d', (slice) => arc(slice) ?? '')
}

/**
 * Keeps a host's label just outside its donut ring. The ring's outer radius
 * depends on the zoom, so the offset has to follow: fitted to screen the wide
 * ring would otherwise overlap the name, and zoomed in the name would sit
 * needlessly far away.
 */
export function refreshHostLabels(nodes: NodeSelection, scale: number): void {
  const y = donutOuterRadius(scale) + 5
  nodes.filter(isKind('host')).select(`text.${flowClass.label}`).attr('y', y)
}

/**
 * The per-frame work: where everything is, and nothing else.
 *
 * Also what redraws the site boxes when a gesture settles — they grow at low
 * zoom so their names stay readable, and that is the same transform.
 */
export function positionNodes(nodes: NodeSelection, scale: number): void {
  const boxScale = siteScaleForZoom(scale)
  nodes.attr('transform', (node) => {
    const x = finiteOr(node.x)
    const y = finiteOr(node.y)
    return node.nodeType === 'site'
      ? `translate(${x},${y}) scale(${boxScale})`
      : `translate(${x},${y})`
  })
}

export function positionLinks(links: LinkSelection): void {
  links
    .attr('x1', (link) => finiteOr(link.source.x))
    .attr('y1', (link) => finiteOr(link.source.y))
    .attr('x2', (link) => finiteOr(link.target.x))
    .attr('y2', (link) => finiteOr(link.target.y))
}

/**
 * Measures how wide each host's service labels actually draw, which is what the
 * row grid's column width has to be. Only the row layout needs it, and only
 * once the labels are in the DOM; before that the names' lengths are the guess.
 *
 * The measurement forces a text layout over every label, so ``widths`` carries
 * what has already been measured across pushes: a label's width follows from
 * its node's id, which does not change, so only nodes new to this render are
 * measured.
 */
export function measureRowSpacings(
  nodes: NodeSelection,
  servicesByHost: ReadonlyMap<string, FNode[]>,
  widths: Map<string, number>
): Map<string, number> {
  const spacings = new Map<string, number>()
  nodes.filter(isKind('service', 'more')).each(function (node) {
    if (widths.has(node.id)) {
      return
    }
    const label = (this as SVGGElement).querySelector<SVGTextElement>(`text.${flowClass.label}`)
    if (label) {
      widths.set(node.id, label.getComputedTextLength())
    }
  })
  for (const [hostId, services] of servicesByHost) {
    if (!showSvcLabel(services.length)) {
      spacings.set(hostId, svcR(services.length) * 2 + 6)
      continue
    }
    let widest = 0
    for (const service of services) {
      widest = Math.max(widest, widths.get(service.id) ?? 0)
    }
    spacings.set(hostId, widest > 0 ? widest + 10 : rowSpacingFallback(services))
  }
  return spacings
}

function isFromSite(link: FLink): boolean {
  return link.source.nodeType === 'site'
}

function labelOf(node: FNode, moreLabel: (count: number) => string): string {
  switch (node.nodeType) {
    case 'more':
      return moreLabel(node.moreCount ?? 0)
    case 'service':
      return serviceNameOf(node.id)
    case 'site':
      return node.siteId ?? ''
    default:
      return node.id
  }
}
