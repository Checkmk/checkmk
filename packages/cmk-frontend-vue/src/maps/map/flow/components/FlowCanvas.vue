<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The drawing of a flow map: its hosts, whatever hangs off them, and the edges
between them, arranged by a force simulation.

The static scaffolding is declared here — the drawing area, the layer the zoom
transform is written onto, and the filter that lifts the worst hosts out of the
map. Everything inside those layers is d3's, because it is rebuilt from a fresh
topology every few seconds and can run into thousands of elements: a Vue
component per node would re-render all of them on every simulation tick, where
d3 writes one attribute per node and nothing else.

So the division is: this component owns the lifecycle and decides what a
gesture means, ``paint`` decides what things look like, ``graph`` decides what
there is to draw, and the composables own the zoom and the search. Where a
click on a node *leads* is the map view's, and is emitted.
-->
<script setup lang="ts">
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { drag } from 'd3-drag'
import type { Simulation } from 'd3-force'
import { select } from 'd3-selection'
import { onUnmounted, shallowRef, toRef, useId, useTemplateRef, watch } from 'vue'

import MapMarqueeBox from '@/maps/map/components/MapMarqueeBox.vue'
import MapOverlayButton from '@/maps/map/components/MapOverlayButton.vue'
import MapZoomResetPill from '@/maps/map/components/MapZoomResetPill.vue'
import { useD3Cleanup } from '@/maps/map/composables/useD3Cleanup'
import { useHoverGrace } from '@/maps/map/composables/useHoverGrace'
import { useMapMotion } from '@/maps/map/composables/useMapMotion'
import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import { ATTENTIONS, type Attention } from '@/maps/map/flow/attention'
import FlowGroupHoverCard, {
  type GroupCardContent
} from '@/maps/map/flow/components/FlowGroupHoverCard.vue'
import { useFlowFilter } from '@/maps/map/flow/composables/useFlowFilter'
import { isSelectable, type useFlowSelection } from '@/maps/map/flow/composables/useFlowSelection'
import { type ViewMark, useFlowZoom } from '@/maps/map/flow/composables/useFlowZoom'
import { createFlowSimulation } from '@/maps/map/flow/forces'
import { finiteOr, summarizeHosts } from '@/maps/map/flow/geometry'
import { FOLD_WIDTH, createFlowGraph, sameSet } from '@/maps/map/flow/graph'
import {
  hostColumnWidth,
  needsServices,
  placeServiceNodes,
  showsDonut
} from '@/maps/map/flow/layout'
import { KIND_TRAITS, isSiteNodeId } from '@/maps/map/flow/nodeIds'
import type { createFlowNodeModel } from '@/maps/map/flow/nodeModel'
import type { FLink, FNode, HostFrame } from '@/maps/map/flow/nodes'
import {
  drawFoldBacks,
  drawFrames,
  drawLinks,
  drawNodes,
  flowClass,
  linkKey,
  measureRowSpacings,
  nodeKindClass,
  positionFoldBacks,
  positionFrames,
  positionLinks,
  positionNodes,
  refreshDonutWidths,
  refreshHostLabels,
  refreshLinks,
  refreshNodes
} from '@/maps/map/flow/paint'
import type { HostLayout, MapElement, ServiceLayout, TopologyNode } from '@/maps/types/api'
import { objectAriaLabel } from '@/maps/utils/objectAria'

/** Where a node was put, in the map's own coordinates. */
interface Position {
  x: number
  y: number
}

/** Height used before the drawing area has been measured. */
const FALLBACK_HEIGHT = 600
/** How long a burst of drags is collected before the map is asked to save. */
const SAVE_DELAY = 400
/** How far the simulation runs before the refining fit stops waiting for it. */
const FIT_TICKS = 30
const FIT_TICKS_WITH_SERVICES = 120

const props = defineProps<{
  topology: TopologyNode[]
  /** How the map reads its nodes: as map objects, states and visual cues. */
  model: ReturnType<typeof createFlowNodeModel>
  /** The nodes the operator has picked, and the band they pick them with. */
  selection: ReturnType<typeof useFlowSelection>
  /** Which of a host's services are on show, and in what shape. */
  layout: ServiceLayout
  hostLayout: HostLayout
  /** Stands in for a site the topology did not tag — a single-site setup. */
  connectionId: string
  /** The positions the map remembers, so a reload keeps the arrangement. */
  savedPositions: Record<string, Position>
  /** Whether a click on a node leads anywhere, which the cursor promises. */
  clickable: boolean
  /** A readonly map still drags — only the saving is withheld. */
  readonly: boolean
  /** The settings preview is not interactive. */
  preview: boolean
  filterNeedle: string
  problemsOnly: boolean
  /** The host whose slide-in was opened by its name, drawn even when it is collapsed. */
  picked: string | null
  /** Changes when this is a different map, or looks at a different root. */
  resetKey: string
  /** Checkmk GUI base, which makes the counts on a group's card links into its views. */
  checkmkUrl: string | null
}>()

const emit = defineEmits<{
  'object-click': [object: MapElement, node: FNode, event: MouseEvent | null]
  'object-context': [object: MapElement, node: FNode, event: MouseEvent]
  'object-hover': [object: MapElement, node: FNode, anchor: HoverAnchorRect]
  'object-hover-leave': []
  /** A host named on a collapsed group's card, which the operator picked. */
  'select-host': [hostName: string]
  /** The operator moved something, and the map should remember where. */
  'positions-changed': [positions: Record<string, Position>]
  /**
   * The hosts the search names: how many, and those drawn, which ``showHit``
   * can bring into view, in the order it steps through them.
   */
  'search-hits': [hits: { total: number; drawn: string[] }]
}>()

const { _t, _tn } = usei18n()

const svgEl = useTemplateRef<SVGSVGElement>('svg')
useD3Cleanup(svgEl)
// Per instance, so two flow maps on one page cannot reference each other's.
const glowFilter = `maps-flow-glow-${useId()}`
/** The nodes of the most recent build by id. */
let nodeById: ReadonlyMap<string, FNode> = new Map()

const graph = createFlowGraph({
  describeTruncation: (count) => _tn('%{n} more service', '%{n} more services', count, { n: count })
})

const filter = useFlowFilter({
  svgEl,
  needle: () => props.filterNeedle,
  problemsOnly: () => props.problemsOnly,
  worstServiceState: props.model.worstServiceState
})

const marquee = props.selection.marquee

let simulation: Simulation<FNode, undefined> | null = null
/** The nodes of the most recent build, which a fit is computed over. */
let drawn: FNode[] = []
/**
 * The parent→child index of the most recent build. A drag handler is bound
 * once, when its node first enters, but has to free the descendants the node
 * has *now* — so it reads this rather than closing over the build it was bound
 * in, whose children a later topology push would no longer match.
 */
let childrenOfDrawn: ReadonlyMap<string, string[]> = new Map()
/**
 * The same for what a site drag carries along: a tree's hosts and their
 * services, which are pinned to their host and would otherwise stay behind
 * while the simulation rests.
 */
let groupOfSite: ReadonlyMap<string, FNode[]> = new Map()
/**
 * The view before each group was opened, which folding it back returns to: the
 * operator gets back the picture they had.
 */
const viewBeforeOpening = new Map<string, ViewMark>()
/** The frames of the most recent build, for what an opened group holds. */
let frames: HostFrame[] = []
/** The anchor maps of the most recent build, which a carried group moves. */
let anchors: { x: Map<string, number>; y: Map<string, number> } = { x: new Map(), y: new Map() }
/** Column widths for the row grid, by host id. */
let rowSpacings = new Map<string, number>()
/**
 * How wide each service label draws, by node id. Measuring forces a text
 * layout, and a label's width follows from its node's id, so it is kept.
 */
let labelWidths = new Map<string, number>()
/**
 * Hosts and site roots whose folded children the operator opened, with how
 * often: each opening shows more of them. Replaced, never mutated.
 */
const opened = shallowRef(new Map<string, number>())
/** What a screen reader hears when a group opens or folds. */
const announcement = shallowRef<TranslatedString>(untranslated(''))
/** The hosts the search names, as of the last render. */
let found = new Set<string>()
/** Whether the last render folded hosts away, which a search may have to undo. */
let folding = false
/**
 * The collapsed group or site the pointer rests on, what its card says as of
 * the last render, and where the card opens.
 */
interface GroupCard {
  id: string
  content: GroupCardContent
  x: number
  y: number
  around: HoverAnchorRect
}
const groupCard = shallowRef<GroupCard | null>(null)
const groupCardGrace = useHoverGrace(() => (groupCard.value = null))
/** Repaints everything at its current position — set by each render. */
let repaint: (() => void) | null = null
let attached = false

const root = useTemplateRef<HTMLDivElement>('root')
const zoom = useFlowZoom({
  svgEl,
  nodes: () => drawn,
  simulation: () => simulation,
  onSettled: refreshAgainstZoom,
  // The nodes that were hidden stopped being positioned while they were; they
  // are put back where they belong before they are seen again.
  onDetailChange: () => repaint?.(),
  motion: useMapMotion(() => root.value)
})
const displayScale = zoom.displayScale
const zoomedByHand = zoom.zoomedByHand

/** What is drawn to a size that depends on the current zoom. */
function refreshAgainstZoom(): void {
  const svg = svgEl.value
  if (!svg) {
    return
  }
  const nodes = select(svg).selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
  refreshDonutWidths(svg, zoom.scale())
  refreshHostLabels(
    nodes,
    zoom.scale(),
    folding
      ? {
          emphasised: (node) =>
            props.model.isWorst(node) ||
            node.state === 'DOWN' ||
            !!(node.foldAttention?.down || node.foldAttention?.unreachable) ||
            found.has(node.id) ||
            opened.value.has(node.id),
          // A name may grow no wider than the room its host takes in a column.
          room: (node) => (node.nodeType === 'host' ? hostColumnWidth(node.id) : FOLD_WIDTH)
        }
      : undefined
  )
  // The site boxes grow at low zoom, which is part of the same transform the
  // per-frame positioning writes.
  positionNodes(
    nodes.filter((node) => node.nodeType === 'site'),
    zoom.scale()
  )
}

// A burst of drags — several hosts in a row, or a group at once — is collected
// into one save rather than hammering the map's update endpoint.
let saveTimer: ReturnType<typeof setTimeout> | null = null
function scheduleSave(): void {
  if (saveTimer) {
    clearTimeout(saveTimer)
  }
  saveTimer = setTimeout(() => emit('positions-changed', graph.pinnedPositions()), SAVE_DELAY)
}

onUnmounted(() => {
  if (saveTimer) {
    clearTimeout(saveTimer)
  }
  simulation?.stop()
})

/** ``hits``: what the search names, where the caller has just worked it out. */
function render(hits?: Set<string>): void {
  const svg = svgEl.value
  const { topology, layout, model, selection } = props
  if (!svg || !topology.length) {
    return
  }
  found = hits ?? filter.foundHosts(topology)
  const built = graph.build({
    topology,
    layout,
    connectionId: props.connectionId,
    savedPositions: props.savedPositions,
    height: svg.clientHeight || FALLBACK_HEIGHT,
    opened: opened.value,
    found,
    problemsOnly: props.problemsOnly,
    picked: props.picked,
    hostLayout: props.hostLayout
  })
  drawn = built.nodes
  nodeById = built.byId
  if (groupCard.value) {
    const live = built.byId.get(groupCard.value.id)
    groupCard.value = live ? { ...groupCard.value, content: groupCardContent(live) } : null
  }
  folding = built.startsAsTree
  reportHits()
  childrenOfDrawn = built.childrenOf
  frames = built.frames
  groupOfSite = new Map(
    built.frames
      .filter((frame) => frame.head.nodeType === 'site')
      .map((frame) => [
        frame.head.id,
        frame.members.flatMap((member) => [member, ...(built.servicesByHost.get(member.id) ?? [])])
      ])
  )
  anchors = { x: built.anchorX, y: built.anchorY }

  const area = select(svg)
  if (!attached) {
    attached = true
    zoom.attach(svg)
    selection.attachMarquee(svg)
  }

  const place = (): void =>
    placeServiceNodes({
      layout,
      hosts: built.byId,
      servicesByHost: built.servicesByHost,
      rowSpacings
    })
  // Before the simulation is built: d3 initialises the nodes it is given, and
  // a service without a place yet would be given a phyllotaxis default.
  place()

  const links = area
    .select<SVGGElement>(`g.${flowClass.links}`)
    .selectAll<SVGPathElement, FLink>('path')
    .data(built.links, linkKey)
  links.exit().remove()
  const entering = links.enter().append('path')
  drawLinks(entering)
  const allLinks = entering.merge(links)
  refreshLinks(allLinks)

  const nodes = area
    .select<SVGGElement>(`g.${flowClass.nodes}`)
    .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
    .data(built.nodes, (node) => node.id)
  nodes.exit().remove()
  const entered = nodes
    .enter()
    .append('g')
    .attr('class', nodeKindClass)
    .attr('cursor', cursorFor)
    .attr('tabindex', 0)
    .attr('role', 'button')
    .on('keydown', onNodeKeydown)
    .on('click', onNodeClick)
    .on('contextmenu', onNodeContextMenu)
    .on('mouseenter', onNodeEnter)
    .on('mouseleave', onNodeLeave)
  drawNodes(entered)
  // A readonly map still drags, so the arrangement feels alive; only the
  // preview opts out. Called directly rather than through ``call`` so the
  // node datum keeps its type.
  if (!props.preview) {
    dragBehaviour()(entered.filter((node) => KIND_TRAITS[node.nodeType].draggable))
  }
  const all = entered.merge(nodes)
  refreshNodes(all, {
    scale: zoom.scale(),
    showsDonut: (node) =>
      node.nodeType === 'fold' || showsDonut(layout, node.topo?.services_omitted),
    glowFilter,
    isWorst: model.isWorst,
    halo: model.hostHalo,
    donutSegments: (node) => node.foldStates ?? (node.topo ? model.donutSegments(node.topo) : []),
    badges: (node) => model.commandMarkers(_t, node),
    ariaLabel: (node) =>
      node.nodeType === 'fold'
        ? foldTitle(node)
        : objectAriaLabel(_t, model.mapElementFromFNode(node), stateNameOf(node)),
    moreLabel: (count) => _tn('+%{n} more', '+%{n} more', count, { n: count }),
    foldLabel
  })

  // The row grid's column width is the one spacing that depends on how long the
  // service names actually draw, so it is measured off what was just painted
  // and fed back into the placement — and into the collide radius below.
  if (layout === 'row') {
    rowSpacings = measureRowSpacings(all, built.servicesByHost, labelWidths)
  }

  // Below the detail threshold the service nodes and their edges are hidden, so
  // there is no point positioning them: on a dense map they are the great
  // majority of what a tick would otherwise write.
  const visibleNodes = all.filter((node) => KIND_TRAITS[node.nodeType].coarse)
  const visibleLinks = allLinks.filter((link) => !link.isServiceLink)
  const frameSelection = drawFrames(
    area.select<SVGGElement>(`g.${flowClass.frames}`).node()!,
    built.frames
  )
  const foldBacks = drawFoldBacks(
    area.select<SVGGElement>(`g.${flowClass.foldBacks}`).node()!,
    built.frames,
    {
      label: (frame) =>
        frame.head.nodeType === 'site'
          ? _t('Collapse the hosts below site %{name}', { name: headName(frame.head) })
          : _t('Collapse the hosts below %{name}', { name: headName(frame.head) }),
      onFold: foldBack
    }
  )
  const noServices = new Map<string, FNode[]>()
  function tick(): void {
    if (zoom.lowDetail()) {
      positionLinks(visibleLinks)
      positionNodes(visibleNodes, zoom.scale())
      positionFrames(frameSelection, noServices)
      positionFoldBacks(foldBacks, zoom.scale())
      return
    }
    place()
    positionLinks(allLinks)
    positionNodes(all, zoom.scale())
    positionFrames(frameSelection, built.servicesByHost)
    positionFoldBacks(foldBacks, zoom.scale())
  }
  repaint = tick

  simulation?.stop()
  simulation = createFlowSimulation({
    nodes: built.nodes,
    springLinks: built.springLinks,
    servicesByHost: built.servicesByHost,
    layout,
    maxLvl: built.maxLvl,
    startsAsTree: built.startsAsTree,
    vSpacing: built.vSpacing,
    anchorX: built.anchorX,
    anchorY: built.anchorY,
    rowSpacings
  })

  // Painted once from the remembered and pre-laid-out positions, so there is
  // something to look at before the simulation has run at all.
  tick()
  zoom.applyDetail()
  refreshAgainstZoom()
  filter.apply()
  selection.apply()

  const firstPaint = zoom.isFirstPaint()
  simulation.on('tick', tick)
  if (firstPaint || built.structurallyChanged) {
    // A flat map starts close to its steady state, so a fraction of the energy
    // settles it. A hierarchy, and any layout with service rings, needs the
    // full relaxation: collide has to push wide rings apart from a tight start.
    // A tree start is already where it should be, rings included, so it only
    // needs settling, which also keeps it the same from one load to the next.
    const settled = built.startsAsTree
    const full = !settled && (built.maxLvl > 0 || needsServices(layout))
    simulation.alpha(firstPaint ? (full ? 1 : 0.4) : settled ? 0.1 : 0.2).restart()
  } else {
    // Nothing structural changed: the colours, rings and halos were refreshed
    // above and the operator's layout stays put. Alpha is driven to zero so a
    // later pan cannot resurrect the freshly built simulation — the constructor
    // leaves it at 1, and the gesture's own resume would then kick every host
    // into a relaxation pass on every push.
    simulation.alpha(0).stop()
  }
  if (firstPaint) {
    zoom.fitFirstPaint(simulation, needsServices(layout) ? FIT_TICKS_WITH_SERVICES : FIT_TICKS)
  }
}

/** What the operator calls the site or host a group hangs from. */
function headName(node: FNode): string {
  return node.nodeType === 'site' ? (node.siteId ?? node.id) : node.id
}

/** What the label under a folded group reads; its ring and badge say what state they are in. */
function foldLabel(node: FNode): string {
  const n = node.moreCount ?? 0
  return _tn('%{n} host', '%{n} hosts', n, { n })
}

/** What a folded group holds, by what its hosts need: its accessible name. */
function foldTitle(node: FNode): string {
  const n = node.moreCount ?? 0
  const counts = node.foldAttention ?? {}
  const parts = ATTENTIONS.flatMap((need) => {
    const count = counts[need] ?? 0
    return count && need !== 'none' ? [foldPart(need, count)] : []
  })
  const args = {
    n,
    parent: node.foldParentName ?? '',
    states: parts.length ? parts.join(', ') : _t('all OK')
  }
  return isSiteNodeId(node.foldParent ?? '')
    ? _tn(
        '%{n} host below site %{parent}: %{states}',
        '%{n} hosts below site %{parent}: %{states}',
        n,
        args
      )
    : _tn('%{n} host below %{parent}: %{states}', '%{n} hosts below %{parent}: %{states}', n, args)
}

function foldPart(need: Exclude<Attention, 'none'>, n: number): string {
  switch (need) {
    case 'down':
      return _tn('%{n} down', '%{n} down', n, { n })
    case 'unreachable':
      return _tn('%{n} unreachable', '%{n} unreachable', n, { n })
    case 'critical':
      return _tn('%{n} with critical services', '%{n} with critical services', n, { n })
    case 'unknown':
      return _tn('%{n} with unknown services', '%{n} with unknown services', n, { n })
    case 'warning':
      return _tn('%{n} with warning services', '%{n} with warning services', n, { n })
    case 'handled':
      return _tn('%{n} with handled problems', '%{n} with handled problems', n, { n })
    case 'pending':
      return _tn('%{n} pending', '%{n} pending', n, { n })
  }
}

/** A node's live state. Only a site's is aggregated, and has to be derived. */
function stateNameOf(node: FNode): string {
  return node.nodeType === 'site' ? props.model.objectStateFromFNode(node).state : node.state
}

function cursorFor(node: FNode): string {
  if (node.nodeType === 'site' || node.nodeType === 'host') {
    return 'grab'
  }
  if (node.nodeType === 'fold') {
    return 'pointer'
  }
  return props.clickable ? 'pointer' : 'default'
}

function onNodeKeydown(event: KeyboardEvent, node: FNode): void {
  if (event.key !== 'Enter' && event.key !== ' ') {
    return
  }
  event.preventDefault()
  if (node.nodeType === 'fold') {
    openFold(node)
    return
  }
  emit('object-click', props.model.mapElementFromFNode(node), node, null)
}

/**
 * Shows the hosts a fold holds, where the fold was. The rest of the map only
 * makes room, and the view goes to the opened group, which is what the
 * operator wants to look at next.
 */
function openFold(node: FNode): void {
  const parentId = node.foldParent
  if (!parentId) {
    return
  }
  const parent = drawn.find((candidate) => candidate.id === parentId)
  if (!parent) {
    return
  }
  groupCardGrace.closeNow()
  const drawnBefore = new Set(drawn.map((candidate) => candidate.id))
  if (!opened.value.has(parentId)) {
    const view = zoom.markView()
    if (view) {
      viewBeforeOpening.set(parentId, view)
    }
  }
  opened.value = new Map(opened.value).set(parentId, (opened.value.get(parentId) ?? 0) + 1)
  render()
  const members = frames.find((frame) => frame.head.id === parentId)?.members ?? []
  zoom.focusOn([parent, ...members])
  const name = headName(parent)
  const shown = drawn.filter(
    (candidate) => candidate.nodeType === 'host' && !drawnBefore.has(candidate.id)
  )
  announcement.value =
    parent.nodeType === 'site'
      ? _tn(
          'Showing %{count} host below site %{name}',
          'Showing %{count} hosts below site %{name}',
          shown.length,
          { count: shown.length, name }
        )
      : _tn(
          'Showing %{count} host below %{name}',
          'Showing %{count} hosts below %{name}',
          shown.length,
          { count: shown.length, name }
        )
  // Keyboard focus would otherwise fall back to the page with the fold that
  // held it; it goes to the button that folds the group back.
  focusIn(flowClass.foldBack, (frame: HostFrame) => frame.head.id === parentId)
}

/**
 * Folds back one group the operator opened, with whatever they opened inside
 * it. The view returns to where it was before the group was opened, unless the
 * operator has moved it since; then the head keeps its place on screen and only
 * the zoom returns, so the group closes where they are looking.
 */
function foldBack(frame: HostFrame): void {
  const inside = new Set([frame.head.id, ...frame.members.map((member) => member.id)])
  opened.value = new Map([...opened.value].filter(([id]) => !inside.has(id)))
  const before = viewBeforeOpening.get(frame.head.id)
  for (const id of inside) {
    viewBeforeOpening.delete(id)
  }
  render()
  if (before && !zoom.returnTo(before) && before.transform.k > zoom.scale()) {
    zoom.zoomAround(frame.head, before.transform.k)
  }
  const name = headName(frame.head)
  announcement.value =
    frame.head.nodeType === 'site'
      ? _t('Collapsed the hosts below site %{name}', { name })
      : _t('Collapsed the hosts below %{name}', { name })
  // Too few hosts to fold, or a search, can leave the group drawn without one.
  const fold = drawn.find((node) => node.foldParent === frame.head.id)
  focusIn(flowClass.node, (node: FNode) => node === (fold ?? nodeById.get(frame.head.id)))
}

/** Moves keyboard focus to the drawn element whose data ``matches``. */
function focusIn<Datum>(kind: string, matches: (datum: Datum) => boolean): void {
  const svg = svgEl.value
  if (!svg) {
    return
  }
  select(svg)
    .selectAll<SVGGElement, Datum>(`g.${kind}`)
    .filter(matches)
    .node()
    ?.focus({ preventScroll: true })
}

let reported: { total: number; drawn: string[] } = { total: 0, drawn: [] }

function reportHits(): void {
  const hits = drawn
    .filter((node) => node.nodeType === 'host' && found.has(node.id))
    .map((node) => node.id)
    .sort()
  const same =
    found.size === reported.total &&
    hits.length === reported.drawn.length &&
    hits.every((id, i) => id === reported.drawn[i])
  if (!same) {
    reported = { total: found.size, drawn: hits }
    emit('search-hits', reported)
  }
}

/**
 * Brings a host the search found into view. The keyboard focus stays in the
 * search, so the next Enter goes on to the next hit.
 */
function showHit(id: string): void {
  const node = drawn.find((candidate) => candidate.id === id)
  if (node) {
    viewBeforeSearch ??= zoom.markView()
    zoom.fitView({ only: [node] })
  }
}

/** Folds back everything the operator opened, and shows the whole map again. */
function foldAll(): void {
  opened.value = new Map()
  viewBeforeOpening.clear()
  render()
  zoom.fitView()
  announcement.value = _t('Collapsed all hosts')
}

function onNodeClick(event: MouseEvent, node: FNode): void {
  // Shift-click builds the selection, which is the canvas's own gesture. Every
  // other click is about where the node leads, which is the map view's.
  if (event.shiftKey && isSelectable(node)) {
    props.selection.toggle(node)
    return
  }
  if (node.nodeType === 'fold') {
    hoverMutedAt = { x: event.clientX, y: event.clientY }
    openFold(node)
    return
  }
  zoom.claimView()
  emit('object-click', props.model.mapElementFromFNode(node), node, event)
}

function onNodeContextMenu(event: MouseEvent, node: FNode): void {
  if (!KIND_TRAITS[node.nodeType].monitored) {
    return
  }
  event.preventDefault()
  emit('object-context', props.model.mapElementFromFNode(node), node, event)
}

/**
 * Where the operator clicked a fold open. A host now lies under the resting
 * pointer where the fold was, and its hover card would cover the very hosts
 * they just opened, as would that of any host the zoom then slides under it;
 * they show once the pointer moves on.
 */
let hoverMutedAt: { x: number; y: number } | null = null

function onNodeEnter(event: MouseEvent, node: FNode): void {
  if (
    hoverMutedAt &&
    Math.abs(event.clientX - hoverMutedAt.x) < 4 &&
    Math.abs(event.clientY - hoverMutedAt.y) < 4
  ) {
    return
  }
  hoverMutedAt = null
  if (props.preview) {
    return
  }
  const group = event.currentTarget as SVGGElement
  if (node.nodeType === 'fold' || node.nodeType === 'site') {
    emit('object-hover-leave')
    groupCardGrace.cancelClose()
    groupCard.value = { id: node.id, content: groupCardContent(node), ...besideGroup(group) }
    return
  }
  const box = group.getBoundingClientRect()
  const around = { left: box.left, top: box.top, right: box.right, bottom: box.bottom }
  groupCardGrace.closeNow()
  if (KIND_TRAITS[node.nodeType].monitored) {
    emit('object-hover', props.model.mapElementFromFNode(node), node, around)
  }
}

/** What the card of a collapsed group or a site says. */
function groupCardContent(node: FNode): GroupCardContent {
  if (node.nodeType === 'site') {
    return {
      name: headName(node),
      subtitle: _t('Site'),
      state: stateNameOf(node),
      summary: props.model.siteSummary(node.siteId ?? ''),
      viewTarget: { site: node.siteId ?? null },
      first: []
    }
  }
  const parent = node.foldParentName ?? ''
  return {
    name: foldLabel(node),
    subtitle: isSiteNodeId(node.foldParent ?? '')
      ? _t('Hosts below site %{site}', { site: parent })
      : _t('Hosts below %{parent}', { parent }),
    state: node.state,
    summary: node.foldSummary ?? summarizeHosts([]),
    viewTarget: { hosts: node.foldMembers ?? [] },
    first: node.foldFirst ?? []
  }
}

/** Beside the group, like a host's card, so it does not cover it. */
function besideGroup(group: SVGGElement): Omit<GroupCard, 'id' | 'content'> {
  const box = group.getBoundingClientRect()
  const around = { left: box.left, top: box.top, right: box.right, bottom: box.bottom }
  return { x: box.right + 8, y: box.top, around }
}

function onNodeLeave(): void {
  if (groupCard.value) {
    groupCardGrace.scheduleClose()
  }
  emit('object-hover-leave')
}

function onGroupCardSelect(hostName: string): void {
  groupCardGrace.closeNow()
  emit('select-host', hostName)
}

/**
 * Dragging pins the dragged node to the cursor and nothing else. Its parents
 * and children follow through the simulation, so they drift after it with a
 * spring's delay rather than tracking the cursor rigidly. A site of a tree is
 * the exception: it carries its frame of hosts along as one piece, without the
 * simulation, so the tree arrives where it is put and no host is re-rastered
 * by physics on the way.
 */
function dragBehaviour() {
  let moved = false
  let carried: FNode[] | undefined
  return drag<SVGGElement, FNode>()
    .on('start', (event, node) => {
      zoom.claimView()
      moved = false
      carried = groupOfSite.get(node.id)
      if (carried) {
        return
      }
      // The simulation is woken here rather than in ``drag``: d3's
      // ``event.active`` is 0 only in start and end, so the textbook gate in
      // ``drag`` would never fire, and a second drag would move the pin without
      // ever ticking it into the node's position.
      if (!event.active) {
        simulation?.alphaTarget(0.3).restart()
      }
      graph.unpinDescendants(node.id, childrenOfDrawn)
    })
    .on('drag', (event, node) => {
      // Stopped on the first move, not on the press, so a bare click does not
      // freeze a simulation that is still settling.
      if (carried && !moved) {
        simulation?.stop()
      }
      moved = true
      if (carried) {
        for (const member of [node, ...carried]) {
          shiftNode(member, event.dx, event.dy)
        }
        repaint?.()
        return
      }
      node.fx = event.x
      node.fy = event.y
    })
    .on('end', (event, node) => {
      // Released even after a bare click: the start above gave the simulation a
      // brief wake that has to be cooled back down.
      if (!event.active) {
        simulation?.alphaTarget(0)
      }
      if (!moved) {
        carried = undefined
        return
      }
      if (carried) {
        // The forces hold each host at its anchor, read once when they start.
        for (const member of carried.filter((m) => KIND_TRAITS[m.nodeType].hostShaped)) {
          anchors.x.set(member.id, finiteOr(member.x))
          anchors.y.set(member.id, finiteOr(member.y))
        }
        simulation?.nodes(simulation.nodes())
        carried = undefined
      }
      if (typeof node.fx === 'number') {
        node.x = node.fx
      }
      if (typeof node.fy === 'number') {
        node.y = node.fy
      }
      // A map the user may not save lets them rearrange it as a playground,
      // and remembers none of it.
      if (!props.readonly) {
        scheduleSave()
      }
      moved = false
    })
}

function shiftNode(node: FNode, dx: number, dy: number): void {
  node.x = finiteOr(node.x) + dx
  node.y = finiteOr(node.y) + dy
  if (typeof node.fx === 'number' && typeof node.fy === 'number') {
    node.fx += dx
    node.fy += dy
  }
}

// A different map, a different root or another host layout: nothing about the
// old arrangement applies, and the next paint fits again.
watch([() => props.resetKey, () => props.hostLayout], () => {
  graph.clear()
  opened.value = new Map()
  viewBeforeOpening.clear()
  rowSpacings = new Map()
  labelWidths = new Map()
  zoom.reset()
})

// A switch of service layout invalidates the placements and asks for a fresh
// fit — the map is about to be a very different shape.
watch(
  () => props.layout,
  (to, from) => {
    graph.forgetLayout(from, to)
    rowSpacings = new Map()
    zoom.reset()
  }
)

watch(
  [
    () => props.topology,
    () => props.layout,
    () => props.hostLayout,
    () => props.problemsOnly,
    svgEl
  ],
  () => render(),
  { flush: 'post' }
)
// A host picked from a list may be collapsed: it is drawn, and brought into
// view only then, so picking a host already in sight does not move the map.
// Once it is no longer picked, the view returns to where it was, unless the
// operator has moved it since.
let viewBeforePicking: ViewMark | null = null
let viewBeforeSearch: ViewMark | null = null
watch(
  () => props.picked,
  (host) => {
    const inSight = drawn.some((node) => node.id === host)
    render()
    if (!host) {
      if (viewBeforePicking) {
        zoom.returnTo(viewBeforePicking)
        viewBeforePicking = null
      }
      return
    }
    const node = inSight ? undefined : drawn.find((candidate) => candidate.id === host)
    if (node) {
      viewBeforePicking ??= zoom.markView()
      zoom.fitView({ only: [node] })
    }
  }
)

// A search can name a host that is folded away, which has to be drawn to be
// found — and, when it names only a few, brought into view, all of them, even
// those that were drawn already. Once the search is cleared, the view returns
// to where it was, unless the operator has moved it since.
const FOCUS_HITS = 20
let focusedHits = new Set<string>()
watch(useDebounceRef(toRef(props, 'filterNeedle')), (needle) => {
  const hits = filter.foundHosts(props.topology)
  if (!needle.trim() && viewBeforeSearch) {
    zoom.returnTo(viewBeforeSearch)
    viewBeforeSearch = null
  }
  if (!folding) {
    // Everything is drawn already; only the count changes.
    found = hits
    reportHits()
    return
  }
  if (!sameSet(hits, found)) {
    render(hits)
  }
  if (sameSet(hits, focusedHits)) {
    return
  }
  focusedHits = hits
  const shown = drawn.filter((node) => hits.has(node.id))
  if (shown.length > 0 && shown.length <= FOCUS_HITS) {
    viewBeforeSearch ??= zoom.markView()
    zoom.fitView({ only: shown })
  }
})

defineExpose({
  fitView: () => zoom.fitView(),
  showHit,
  zoomIn: () => zoom.zoomIn(),
  zoomOut: () => zoom.zoomOut(),
  /** The area everything is drawn in, for whoever reads it back. */
  drawingArea: () => svgEl.value
})
</script>

<template>
  <div ref="root" class="maps-flow-canvas">
    <svg ref="svg" class="maps-flow-canvas__svg">
      <defs>
        <!-- A soft halo around the worst-affected hosts, so they stand out even
             fitted to screen, where a stroke width alone disappears. -->
        <filter :id="glowFilter" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g class="maps-flow-canvas__zoom-layer">
        <g class="maps-flow-canvas__frames" />
        <g class="maps-flow-canvas__links" />
        <g class="maps-flow-canvas__nodes" />
        <g class="maps-flow-canvas__fold-backs" />
      </g>
    </svg>

    <FlowGroupHoverCard
      v-if="groupCard"
      :content="groupCard.content"
      :checkmk-url="checkmkUrl"
      :x="groupCard.x"
      :y="groupCard.y"
      :around="groupCard.around"
      @card-enter="groupCardGrace.cancelClose()"
      @card-leave="groupCardGrace.scheduleClose()"
      @select-host="onGroupCardSelect"
    />

    <MapMarqueeBox v-if="marquee.visible.value" :rect="marquee.rect.value" :layer="4" />

    <CmkVisuallyHidden :text="announcement" live="polite" />

    <MapOverlayButton
      v-if="opened.size && !preview"
      class="maps-flow-canvas__fold-all"
      @click="foldAll"
    >
      {{ _t('Collapse all') }}
    </MapOverlayButton>

    <MapZoomResetPill
      :zoom="displayScale"
      :visible="zoomedByHand"
      :offset="{ bottom: '98px', left: '16px' }"
      @reset="zoom.fitView()"
    />
  </div>
</template>

<style scoped>
.maps-flow-canvas {
  /* A tree edge keeps its full state colour on a light canvas, where mixing
     it with the canvas would wash it out; on a dark one it is toned down. */
  --maps-flow-canvas-elbow-share: 100%;

  position: absolute;
  inset: 0;
  overflow: hidden;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .maps-flow-canvas {
  --maps-flow-canvas-elbow-share: 60%;
}

.maps-flow-canvas__svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* The panned and zoomed subtree gets its own composited layer, so the browser
   rasterizes it once and translates the layer per frame instead of repainting
   every host and service ring at every step of the gesture. */
.maps-flow-canvas__zoom-layer {
  will-change: transform;
}

/* While the view moves, hit-testing is suppressed across the whole
   subtree: without it every pointermove walks thousands of SVG descendants to
   work out a hover target the operator cannot reach mid-move anyway. */
[data-map-moving] .maps-flow-canvas__zoom-layer {
  pointer-events: none;
}

/* Beside the zoom controls, which sit in the top left corner. */
.maps-flow-canvas__fold-all {
  position: absolute;
  top: var(--dimension-5);
  left: calc(var(--dimension-5) * 2 + var(--dimension-9));
}

/* The nodes and edges below are drawn by d3, so they carry no scope attribute
   of their own and have to be reached into. All of it has to be CSS: a
   pseudo-class cannot be written from script at all, the selection ring has to
   be able to win over the halo, and hiding the service nodes with one class on
   the root is the whole point — styling thousands of them one by one stutters
   mid-zoom. */
/* stylelint-disable selector-pseudo-class-no-unknown -- ``deep`` is Vue's own,
   and these elements are d3's rather than Vue's. */

/* Opening or folding a group by a click moves the focus from script, which the
   browser outlines on ``:focus`` too; only the keyboard's focus is ringed. */
:deep(.maps-flow-canvas__node:focus) {
  outline: none;
}

/* The name is a node's widest and lowest part, so the ring keeps clear of its letters. */
:deep(.maps-flow-canvas__node:focus-visible) {
  outline: revert;
  outline-offset: 4px;
}

/* A host's halo: which state it reports, written on the group as two custom
   properties by ``paint``. The fallback is the hairline every node gets. */
:deep(.maps-flow-canvas__node > circle) {
  stroke: var(--maps-flow-canvas-halo, rgb(0 0 0 / 40%));
  stroke-width: var(--maps-flow-canvas-halo-width, 1.5);
}

:deep(.maps-flow-canvas__node--service > circle),
:deep(.maps-flow-canvas__node--more > circle) {
  stroke-width: 1;
}

/* A frame: which hosts belong together, quiet enough to stay behind them. */
:deep(.maps-flow-canvas__frame > rect) {
  fill: var(--ux-theme-2);
  fill-opacity: 0.35;
  stroke: var(--default-border-color);
  stroke-width: 1;
  pointer-events: none;
}

/* What the operator opened stands out from the site around it. */
:deep(.maps-flow-canvas__frame--opened > rect) {
  fill: var(--interactive-accent);
  fill-opacity: 0.06;
  stroke: var(--interactive-accent);
  stroke-dasharray: 6 4;
}

:deep(.maps-flow-canvas__fold-back) {
  cursor: pointer;
}

:deep(.maps-flow-canvas__fold-back-hit) {
  fill: transparent;
}

:deep(.maps-flow-canvas__fold-back > circle:not(.maps-flow-canvas__fold-back-hit)) {
  fill: var(--ux-theme-3);
  stroke: var(--interactive-accent);
  stroke-width: 1.5;
}

:deep(.maps-flow-canvas__fold-back > path) {
  stroke: var(--font-color);
  stroke-width: 2;
  stroke-linecap: round;
}

:deep(.maps-flow-canvas__fold-back:hover > circle:not(.maps-flow-canvas__fold-back-hit)),
:deep(.maps-flow-canvas__fold-back:focus-visible > circle:not(.maps-flow-canvas__fold-back-hit)) {
  fill: color-mix(in srgb, var(--interactive-accent) 30%, var(--ux-theme-3));
}

/* The badge is round, so its focus ring is too, rather than the browser's box.
   On ``:focus``: opening a group moves the focus here from script, which the
   browser does not count as ``:focus-visible`` but still outlines. */
:deep(.maps-flow-canvas__fold-back:focus) {
  outline: none;
}

:deep(.maps-flow-canvas__fold-back:focus > .maps-flow-canvas__fold-back-hit) {
  stroke: var(--interactive-accent);
  stroke-width: 2;
}

/* A host's name, which ``refreshHostLabels`` grows inline for the hosts a tree
   keeps readable; a site's and a service's set their own. */
:deep(.maps-flow-canvas__label) {
  font-size: var(--font-size-normal);
}

/* A folded group reads as several hosts, not one. The halo's shadow would
   vanish on the dark theme, so its dashes take the dimmed font colour. */
:deep(.maps-flow-canvas__node--fold > circle) {
  stroke: var(--font-color-dimmed);
  stroke-dasharray: 4 3;
}

/* Last of the three, so it wins at equal specificity. */
:deep(.maps-flow-canvas__node--selected > circle) {
  stroke: var(--interactive-accent);
  stroke-width: 3;
}

.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__node--service),
.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__node--more),
.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__link--service) {
  display: none;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
