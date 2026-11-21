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
 */
import type { Selection } from 'd3-selection'
import { select } from 'd3-selection'

import { onStateColorVar, stateColorVar } from '@/maps/utils/stateColors'

import { unhandledIn } from './attention'
import {
  DONUT_MAX_WIDTH,
  type DonutArc,
  type DonutSegment,
  NODE_R,
  buildDonutArc,
  donutOuterRadius,
  donutPie,
  finiteOr,
  foldArc,
  showSvcLabel,
  svcR
} from './geometry'
import { hostColumnWidth, hostLabelLines, rowSpacingFallback, siteScaleForZoom } from './layout'
import { KIND_TRAITS, serviceNameOf } from './nodeIds'
import type { CmdMarker, FLink, FNode, HostFrame } from './nodes'

/**
 * The classes the drawn parts carry. Shared, because the search, the selection
 * and the stylesheet all reach for the same elements the painter makes.
 */
export const flowClass = {
  zoomLayer: 'maps-flow-canvas__zoom-layer',
  frames: 'maps-flow-canvas__frames',
  frame: 'maps-flow-canvas__frame',
  foldBacks: 'maps-flow-canvas__fold-backs',
  foldBack: 'maps-flow-canvas__fold-back',
  links: 'maps-flow-canvas__links',
  nodes: 'maps-flow-canvas__nodes',
  link: 'maps-flow-canvas__link',
  serviceLink: 'maps-flow-canvas__link--service',
  node: 'maps-flow-canvas__node',
  donut: 'maps-flow-canvas__donut',
  glyph: 'maps-flow-canvas__glyph',
  label: 'maps-flow-canvas__label',
  badges: 'maps-flow-canvas__badges',
  badge: 'maps-flow-canvas__badge',
  foldAlert: 'maps-flow-canvas__fold-alert'
} as const

/** A node kind as a class modifier, so the stylesheet can single one out. */
export function nodeKindClass(node: FNode): string {
  return `${flowClass.node} ${flowClass.node}--${node.nodeType}`
}

export type NodeSelection = Selection<SVGGElement, FNode, SVGGElement, unknown>
export type LinkSelection = Selection<SVGPathElement, FLink, SVGGElement, unknown>
export type FrameSelection = Selection<SVGGElement, HostFrame, SVGGElement, unknown>

/** What the stylesheet reads a host's halo from — see ``FlowCanvas``. */
const HALO_COLOR_PROPERTY = '--maps-flow-canvas-halo'
const HALO_WIDTH_PROPERTY = '--maps-flow-canvas-halo-width'
const FOLD_ALERT_R = 9

/** A site link carries no state of its own, so it takes the muted text colour. */
const SITE_LINK_COLOR = 'var(--font-color-dimmed)'
/** What the flow map is drawn on. */
const CANVAS_COLOR = 'var(--ux-theme-1)'
const GLYPH_COLOR = 'rgb(255 255 255 / 90%)'
const MORE_GLYPH_COLOR = 'rgb(255 255 255 / 95%)'
const FOLD_FILL = 'var(--ux-theme-3)'
/** How much of its state colour a tree edge keeps, per theme; set in ``FlowCanvas``. */
const ELBOW_STATE_SHARE = 'var(--maps-flow-canvas-elbow-share)'
/** Smallest a highlighted host's name may draw on screen, in pixels. */
const LABEL_MIN_SCREEN_PX = 11
/** How far a highlighted host's name may grow against the zoom. */
const LABEL_MAX_GROWTH = 3
/** Below this zoom an ordinary name draws too small to read, and is left out. */
const LABEL_HIDE_SCALE = 0.55
/** A character's width in a label, relative to its font size. */
const LABEL_CHAR_WIDTH = 0.6

// Font size and letter spacing have to be styles: the theme's ``* { font-size:
// inherit; letter-spacing: … }`` beats the SVG attributes.
function px(size: number): string {
  return `${size}px`
}

/** A fold's count in its ring: four characters fit at 10px, a fifth needs 9px. */
function foldCountSize(count: number): string {
  if (count > 9999) {
    return '8px'
  }
  return count > 999 ? '9px' : '10px'
}

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
  /** What the label under a folded group of hosts reads, translated. */
  foldLabel: (node: FNode) => string
}

const isKind =
  (...kinds: FNode['nodeType'][]) =>
  (node: FNode): boolean =>
    kinds.includes(node.nodeType)
const isHostShaped = (node: FNode): boolean => KIND_TRAITS[node.nodeType].hostShaped

/** Builds the shape of each newly entered node, by kind. */
export function drawNodes(enter: NodeSelection): void {
  drawSiteNode(enter.filter(isKind('site')))
  // A folded group looks like a host — it stands where its hosts would — and
  // reads "+N" where a host reads "H".
  drawHostNode(enter.filter(isHostShaped))
  const folds = enter.filter(isKind('fold')).attr('aria-expanded', 'false')
  // How many of the hosts a fold holds need attention, in a corner of it: the
  // ring alone says so only in colour, and only to the eye that finds it.
  const alert = folds
    .append('g')
    .attr('class', flowClass.foldAlert)
    .attr('pointer-events', 'none')
    .attr('transform', `translate(${NODE_R * 0.72},${-NODE_R * 0.72})`)
  alert.append('circle').attr('r', FOLD_ALERT_R).style('stroke', CANVAS_COLOR)
  alert
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .style('font-size', px(10))
    .attr('font-weight', '700')
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
    .style('font-size', px(9))
    .attr('font-weight', '600')
    .style('letter-spacing', '0.08em')
    .attr('pointer-events', 'none')
    .attr('y', -8)
    .style('fill', 'var(--font-color-dimmed)')
    .text('SITE')
  enter
    .append('text')
    .attr('class', flowClass.label)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .style('font-size', px(13))
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
    .style('font-size', px(11))
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .style('fill', GLYPH_COLOR)
    .text('H')
  enter
    .append('text')
    .attr('class', flowClass.label)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
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
  size: (node: FNode) => string
  color: string
}

const SERVICE_GLYPH: GlyphSpec = {
  text: () => 'S',
  size: (node) => (svcR(node.svcTotalCount ?? 1) <= 7 ? '6px' : '8px'),
  color: GLYPH_COLOR
}

const MORE_GLYPH: GlyphSpec = {
  text: (node) => `+${node.moreCount ?? 0}`,
  size: (node) => (svcR(node.svcTotalCount ?? 1) <= 7 ? '7px' : '9px'),
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
    .style('font-size', 'var(--font-size-small)')
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
    .style('font-size', SERVICE_GLYPH.size)
    .text(SERVICE_GLYPH.text)
  merge
    .filter(isKind('more'))
    .select(`text.${flowClass.glyph}`)
    .style('font-size', MORE_GLYPH.size)
    .text(MORE_GLYPH.text)
}

interface LinkStyle {
  opacity: number
  width: number
  dash: string | null
}

/** Everything about how an edge is drawn but its colour, which follows its source's state. */
function linkStyle(link: FLink): LinkStyle {
  if (isFromSite(link)) {
    return { opacity: 0.55, width: 1, dash: '2,3' }
  }
  const opacity = link.elbow ? 1 : link.isServiceLink ? 0.3 : 0.45
  // A host's further parents are dashed, as a second reporting line is on an
  // org chart: they matter to whether it is reachable, but the tree is how
  // it is read.
  if (link.furtherParent) {
    return { opacity, width: 1, dash: '6,4' }
  }
  return link.isServiceLink
    ? { opacity, width: 1, dash: '3,3' }
    : { opacity, width: 1.5, dash: null }
}

/**
 * Joins an edge to its path by its ends and its style, so an edge drawn
 * differently after a push, as a further parent's say, gets a fresh path.
 */
export function linkKey(link: FLink): string {
  const { opacity, width, dash } = linkStyle(link)
  return `${link.source.id}→${link.target.id} ${opacity} ${width} ${dash}`
}

/** How an edge is drawn but its colour, written once: ``linkKey`` joins on it. */
export function drawLinks(enter: LinkSelection): void {
  enter
    .attr('fill', 'none')
    .attr('class', (link) =>
      link.isServiceLink ? `${flowClass.link} ${flowClass.serviceLink}` : flowClass.link
    )
    .each(function (link) {
      const { opacity, width, dash } = linkStyle(link)
      this.setAttribute('stroke-opacity', String(opacity))
      this.setAttribute('stroke-width', String(width))
      if (dash !== null) {
        this.setAttribute('stroke-dasharray', dash)
      }
    })
}

/** The one thing about an edge that a topology push can have changed. */
export function refreshLinks(merge: LinkSelection): void {
  merge.style('stroke', (link) => {
    if (isFromSite(link)) {
      return SITE_LINK_COLOR
    }
    // A parent's tree edges overlap where they share a line; a translucent
    // stroke would turn that line solid, so they are opaque and dimmed instead.
    return link.elbow
      ? `color-mix(in srgb, ${stateColorVar(link.source.state)} ${ELBOW_STATE_SHARE}, ${CANVAS_COLOR})`
      : stateColorVar(link.source.state)
  })
}

/** Writes everything a topology push can have changed about the nodes. */
export function refreshNodes(merge: NodeSelection, visuals: NodeVisuals): void {
  // The accessible name follows the live state, so it is rewritten every time.
  merge.attr('aria-label', visuals.ariaLabel)
  // A folded group holds hosts that need no urgent attention, so it is drawn
  // quieter than the hosts around it rather than in their state colour.
  merge
    .select('circle')
    .style('fill', (node) => (node.nodeType === 'fold' ? FOLD_FILL : stateColorVar(node.state)))
  merge
    .filter((node) => node.nodeType !== 'host')
    .select(`text.${flowClass.label}`)
    .text((node) => labelOf(node, visuals))
  merge
    .filter(isKind('host'))
    .select<SVGTextElement>(`text.${flowClass.label}`)
    .selectAll('tspan')
    .data((node) => hostLabelLines(node.id))
    .join('tspan')
    .attr('x', 0)
    .attr('dy', (_, index) => (index ? '1.2em' : null))
    .text((line) => line)
  refreshServiceLikeNodes(merge)
  const folds = merge.filter(isKind('fold'))
  folds
    .select(`text.${flowClass.glyph}`)
    .style('font-size', (node) => foldCountSize(node.moreCount ?? 0))
    .style('fill', 'var(--font-color)')
    .text((node) => `+${node.moreCount ?? 0}`)
  const alerts = folds.select<SVGGElement>(`g.${flowClass.foldAlert}`)
  alerts.style('display', (node) => (unhandledIn(node.foldAttention) ? null : 'none'))
  alerts.select('circle').style('fill', (node) => stateColorVar(node.state))
  alerts
    .select('text')
    .style('fill', (node) => onStateColorVar(node.state))
    .text((node) => {
      const count = unhandledIn(node.foldAttention)
      return count > 99 ? '99+' : String(count)
    })

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
  refreshDonuts(merge.filter(isHostShaped), visuals)
  refreshBadges(merge.filter(isKind('host', 'service')), visuals.badges)
}

/**
 * Binds each host's aggregated service states as proportional arcs. Which hosts
 * get a ring is the caller's rule; ``exit`` clears the paths of a host that
 * has just stopped qualifying.
 */
function refreshDonuts(hosts: NodeSelection, visuals: NodeVisuals): void {
  const hostArc = buildDonutArc(visuals.scale)
  hosts.each(function (node) {
    const arc = node.nodeType === 'fold' ? foldArc : hostArc
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
      .style('font-size', px(badgeR * 1.3))
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
    .selectAll<SVGPathElement, DonutArc>(`g.${flowClass.node}--host g.${flowClass.donut} path`)
    .attr('d', (slice) => arc(slice) ?? '')
}

/**
 * Keeps a host's label just outside its donut ring. The ring's outer radius
 * depends on the zoom, so the offset has to follow: fitted to screen the wide
 * ring would otherwise overlap the name, and zoomed in the name would sit
 * needlessly far away.
 */
export function refreshHostLabels(
  nodes: NodeSelection,
  scale: number,
  /** In a tree: which names stay readable, and how wide each may grow. */
  tree?: { emphasised: (node: FNode) => boolean; room: (node: FNode) => number }
): void {
  const labels = nodes
    .filter(isHostShaped)
    .select<SVGTextElement>(`text.${flowClass.label}`)
    .attr('y', donutOuterRadius(scale) + 5)
  if (!tree) {
    labels.style('font-size', null).style('display', null)
    nodes.filter(isKind('fold')).select(`text.${flowClass.glyph}`).style('display', null)
    return
  }
  // The hosts that need attention keep a readable name when the tree is fitted
  // to screen. Every other name is left out by then: it could not be read, and
  // it would only collide with the names that can.
  const grown = Math.min(LABEL_MAX_GROWTH, Math.max(1, 1 / finiteOr(scale, 1)))
  const size = (node: FNode, label: string): number => {
    const chars =
      node.nodeType === 'host'
        ? Math.max(...hostLabelLines(node.id).map((line) => line.length))
        : label.length
    const fits = tree.room(node) / (chars * LABEL_CHAR_WIDTH)
    return Math.max(LABEL_MIN_SCREEN_PX, Math.min(LABEL_MIN_SCREEN_PX * grown, fits))
  }
  labels
    .style('font-size', function (node) {
      return tree.emphasised(node) ? px(size(node, this.textContent ?? '')) : null
    })
    .style('display', (node) =>
      tree.emphasised(node) || scale >= LABEL_HIDE_SCALE ? null : 'none'
    )
  // A fold's count is too small to read by then; the names that matter say it.
  nodes
    .filter(isKind('fold'))
    .select(`text.${flowClass.glyph}`)
    .style('display', () => (scale >= LABEL_HIDE_SCALE ? null : 'none'))
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

/** Room around a host's centre that its frame leaves: the ring, and the label below. */
const FRAME_PAD_SIDE = NODE_R * 3
const FRAME_PAD_BOTTOM = NODE_R * 3 + 16
/** How far an opened group's frame sits inside the site frame around it. */
const FRAME_INSET = 12
/**
 * Binds the frames, behind the edges. A site's box sits on its frame's top
 * edge, so the frame reads as the site's.
 */
export function drawFrames(layer: SVGGElement, frames: HostFrame[]): FrameSelection {
  const groups = select(layer)
    .selectAll<SVGGElement, HostFrame>(`g.${flowClass.frame}`)
    .data(frames, (frame) => `${frame.head.id}|${frame.opened}`)
  groups.exit().remove()
  const entered = groups
    .enter()
    .append('g')
    .attr('class', (frame) =>
      frame.opened ? `${flowClass.frame} ${flowClass.frame}--opened` : flowClass.frame
    )
  entered.append('rect').attr('rx', 16)
  return entered.merge(groups)
}

/** A fold-back badge: small enough to sit on its head's edge, a hit area around it big enough to aim at. */
const FOLD_BACK_R = 9
const FOLD_BACK_HIT_R = 12
/** How far the badge grows against the zoom: no further than its head does. */
const FOLD_BACK_MAX_SCALE = 1.5

/**
 * Binds a "−" badge on the head of each group the operator opened, which folds
 * the group back. A tree's open state belongs to the parent, as in a mind map or
 * a file tree: the badge sits on the head's edge where its children's edges
 * leave, and is part of the head rather than a node of its own.
 */
export function drawFoldBacks(
  layer: SVGGElement,
  frames: HostFrame[],
  foldBack: { label: (frame: HostFrame) => string; onFold: (frame: HostFrame) => void }
): FrameSelection {
  const badges = select(layer)
    .selectAll<SVGGElement, HostFrame>(`g.${flowClass.foldBack}`)
    .data(
      frames.filter((frame) => frame.opened),
      (frame) => frame.head.id
    )
  badges.exit().remove()
  const entered = badges
    .enter()
    .append('g')
    .attr('class', flowClass.foldBack)
    .attr('role', 'button')
    .attr('tabindex', 0)
    .attr('aria-expanded', 'true')
    .on('click', (event: MouseEvent, frame) => {
      event.stopPropagation()
      foldBack.onFold(frame)
    })
    .on('keydown', (event: KeyboardEvent, frame) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        foldBack.onFold(frame)
      }
    })
  entered.append('title')
  entered.append('circle').attr('class', `${flowClass.foldBack}-hit`).attr('r', FOLD_BACK_HIT_R)
  entered.append('circle').attr('r', FOLD_BACK_R)
  entered
    .append('path')
    .attr('d', `M${-FOLD_BACK_R / 2},0H${FOLD_BACK_R / 2}`)
    .attr('pointer-events', 'none')
  const all = entered.merge(badges)
  all.attr('aria-label', foldBack.label)
  all.select('title').text(foldBack.label)
  return all
}

/** Puts each fold-back badge on the right edge of its head: a host's ring, or a site's box. */
export function positionFoldBacks(badges: FrameSelection, scale: number): void {
  const badgeScale = Math.min(FOLD_BACK_MAX_SCALE, siteScaleForZoom(scale))
  const edge = (head: FNode): number =>
    head.nodeType === 'site' ? (SITE_WIDTH / 2) * siteScaleForZoom(scale) : donutOuterRadius(scale)
  badges.attr(
    'transform',
    ({ head }) =>
      `translate(${finiteOr(head.x) + edge(head)},${finiteOr(head.y)}) scale(${badgeScale})`
  )
}

/**
 * Fits each frame around its head and members. Runs per frame, so it reads
 * the positions as they are; a few hundred comparisons per frame.
 */
export function positionFrames(
  frames: FrameSelection,
  servicesByHost: ReadonlyMap<string, FNode[]>
): void {
  frames.each(function ({ head, members }) {
    const inset = head.nodeType === 'site' ? 0 : FRAME_INSET
    const top = finiteOr(head.y) - (head.nodeType === 'site' ? 0 : NODE_R + FRAME_INSET)
    let left = finiteOr(head.x)
    let right = left
    let bottom = top
    const include = (node: FNode, side: number, below: number): void => {
      const x = finiteOr(node.x)
      const y = finiteOr(node.y)
      left = Math.min(left, x - side)
      right = Math.max(right, x + side)
      bottom = Math.max(bottom, y + below)
    }
    for (const member of head.nodeType === 'site' ? members : [head, ...members]) {
      // Wide enough for the label, and for a grid's edges, which run beside it.
      const side =
        member.nodeType === 'host'
          ? Math.max(FRAME_PAD_SIDE, hostColumnWidth(member.id) / 2 + 2 * FRAME_INSET)
          : FRAME_PAD_SIDE
      include(member, side - inset, FRAME_PAD_BOTTOM - inset)
      for (const service of servicesByHost.get(member.id) ?? []) {
        include(service, NODE_R * 2, NODE_R * 2)
      }
    }
    const frame = select(this)
    frame
      .select('rect')
      .attr('x', left)
      .attr('y', top)
      .attr('width', right - left)
      .attr('height', bottom - top)
  })
}

export function positionLinks(links: LinkSelection): void {
  links.attr('d', (link) => {
    const sx = finiteOr(link.source.x)
    const sy = finiteOr(link.source.y)
    const tx = finiteOr(link.target.x)
    const ty = finiteOr(link.target.y)
    if (!link.elbow) {
      return `M${sx},${sy}L${tx},${ty}`
    }
    const { drop, aside, rise, reach } = link.elbow
    return `M${sx},${sy}H${sx + drop - rise}V${ty + aside}H${tx - reach}V${ty}H${tx}`
  })
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

function labelOf(node: FNode, visuals: NodeVisuals): string {
  switch (node.nodeType) {
    case 'more':
      return visuals.moreLabel(node.moreCount ?? 0)
    case 'fold':
      return visuals.foldLabel(node)
    case 'service':
      return serviceNameOf(node.id)
    case 'site':
      return node.siteId ?? ''
    default:
      return node.id
  }
}
