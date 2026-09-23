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
import usei18n from 'cmk-ui-library/lib/i18n'
import { drag } from 'd3-drag'
import type { Simulation } from 'd3-force'
import { select } from 'd3-selection'
import { onUnmounted, useId, useTemplateRef, watch } from 'vue'

import MapMarqueeBox from '@/maps/map/components/MapMarqueeBox.vue'
import MapZoomResetPill from '@/maps/map/components/MapZoomResetPill.vue'
import { useD3Cleanup } from '@/maps/map/composables/useD3Cleanup'
import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import { useFlowFilter } from '@/maps/map/flow/composables/useFlowFilter'
import { isSelectable, type useFlowSelection } from '@/maps/map/flow/composables/useFlowSelection'
import { useFlowZoom } from '@/maps/map/flow/composables/useFlowZoom'
import { createFlowSimulation } from '@/maps/map/flow/forces'
import { createFlowGraph } from '@/maps/map/flow/graph'
import { needsServices, placeServiceNodes, showsDonut } from '@/maps/map/flow/layout'
import type { createFlowNodeModel } from '@/maps/map/flow/nodeModel'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import {
  drawLinks,
  drawNodes,
  flowClass,
  measureRowSpacings,
  nodeKindClass,
  positionLinks,
  positionNodes,
  refreshDonutWidths,
  refreshHostLabels,
  refreshLinks,
  refreshNodes
} from '@/maps/map/flow/paint'
import type { MapElement, ServiceLayout, TopologyNode } from '@/maps/types/api'
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
  /** Changes when this is a different map, or looks at a different root. */
  resetKey: string
}>()

const emit = defineEmits<{
  'object-click': [object: MapElement, node: FNode, event: MouseEvent | null]
  'object-context': [object: MapElement, node: FNode, event: MouseEvent]
  'object-hover': [object: MapElement, node: FNode, anchor: HoverAnchorRect]
  'object-hover-leave': []
  /** The operator moved something, and the map should remember where. */
  'positions-changed': [positions: Record<string, Position>]
}>()

const { _t, _tn } = usei18n()

const svgEl = useTemplateRef<SVGSVGElement>('svg')
useD3Cleanup(svgEl)
// Per instance, so two flow maps on one page cannot reference each other's.
const glowFilter = `maps-flow-glow-${useId()}`

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
/** Column widths for the row grid, by host id. */
let rowSpacings = new Map<string, number>()
/**
 * How wide each service label draws, by node id. Measuring forces a text
 * layout, and a label's width follows from its node's id, so it is kept.
 */
let labelWidths = new Map<string, number>()
/** Repaints everything at its current position — set by each render. */
let repaint: (() => void) | null = null
let attached = false

const zoom = useFlowZoom({
  svgEl,
  nodes: () => drawn,
  simulation: () => simulation,
  onSettled: refreshAgainstZoom,
  // The nodes that were hidden stopped being positioned while they were; they
  // are put back where they belong before they are seen again.
  onDetailChange: () => repaint?.()
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
  refreshHostLabels(nodes, zoom.scale())
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

function render(): void {
  const svg = svgEl.value
  const { topology, layout, model, selection } = props
  if (!svg || !topology.length) {
    return
  }
  const built = graph.build({
    topology,
    layout,
    connectionId: props.connectionId,
    savedPositions: props.savedPositions,
    height: svg.clientHeight || FALLBACK_HEIGHT
  })
  drawn = built.nodes
  childrenOfDrawn = built.childrenOf

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
    .selectAll<SVGLineElement, FLink>('line')
    .data(built.links, (link) => `${link.source.id}→${link.target.id}`)
  links.exit().remove()
  const entering = links.enter().append('line')
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
    .on('mouseleave', () => emit('object-hover-leave'))
  drawNodes(entered)
  // A readonly map still drags, so the arrangement feels alive; only the
  // preview opts out. Called directly rather than through ``call`` so the
  // node datum keeps its type.
  if (!props.preview) {
    dragBehaviour()(entered.filter((node) => node.nodeType === 'host' || node.nodeType === 'site'))
  }
  const all = entered.merge(nodes)
  refreshNodes(all, {
    scale: zoom.scale(),
    showsDonut: (node) => showsDonut(layout, node.topo?.services_omitted),
    glowFilter,
    isWorst: model.isWorst,
    halo: model.hostHalo,
    donutSegments: (node) => (node.topo ? model.donutSegments(node.topo) : []),
    badges: (node) => model.commandMarkers(_t, node),
    ariaLabel: (node) => objectAriaLabel(_t, model.mapElementFromFNode(node), stateNameOf(node)),
    moreLabel: (count) => _tn('+%{n} more', '+%{n} more', count, { n: count })
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
  const visibleNodes = all.filter((node) => node.nodeType === 'host' || node.nodeType === 'site')
  const visibleLinks = allLinks.filter((link) => !link.isServiceLink)
  function tick(): void {
    if (zoom.lowDetail()) {
      positionLinks(visibleLinks)
      positionNodes(visibleNodes, zoom.scale())
      return
    }
    place()
    positionLinks(allLinks)
    positionNodes(all, zoom.scale())
  }
  repaint = tick

  simulation?.stop()
  simulation = createFlowSimulation({
    nodes: built.nodes,
    springLinks: built.springLinks,
    servicesByHost: built.servicesByHost,
    layout,
    maxLvl: built.maxLvl,
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
    const full = built.maxLvl > 0 || needsServices(layout)
    simulation.alpha(firstPaint ? (full ? 1 : 0.4) : 0.2).restart()
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

/** A node's live state. Only a site's is aggregated, and has to be derived. */
function stateNameOf(node: FNode): string {
  return node.nodeType === 'site' ? props.model.objectStateFromFNode(node).state : node.state
}

function cursorFor(node: FNode): string {
  if (node.nodeType === 'site' || node.nodeType === 'host') {
    return 'grab'
  }
  return props.clickable ? 'pointer' : 'default'
}

function onNodeKeydown(event: KeyboardEvent, node: FNode): void {
  if (event.key !== 'Enter' && event.key !== ' ') {
    return
  }
  event.preventDefault()
  emit('object-click', props.model.mapElementFromFNode(node), node, null)
}

function onNodeClick(event: MouseEvent, node: FNode): void {
  // Shift-click builds the selection, which is the canvas's own gesture. Every
  // other click is about where the node leads, which is the map view's.
  if (event.shiftKey && isSelectable(node)) {
    props.selection.toggle(node)
    return
  }
  zoom.claimView()
  emit('object-click', props.model.mapElementFromFNode(node), node, event)
}

function onNodeContextMenu(event: MouseEvent, node: FNode): void {
  if (node.nodeType === 'site') {
    return
  }
  event.preventDefault()
  emit('object-context', props.model.mapElementFromFNode(node), node, event)
}

function onNodeEnter(event: MouseEvent, node: FNode): void {
  if (props.preview || node.nodeType === 'site') {
    return
  }
  const box = (event.currentTarget as SVGGElement).getBoundingClientRect()
  emit('object-hover', props.model.mapElementFromFNode(node), node, {
    left: box.left,
    top: box.top,
    right: box.right,
    bottom: box.bottom
  })
}

/**
 * Dragging pins the dragged node to the cursor and nothing else. Its parents
 * and children follow through the simulation, so they drift after it with a
 * spring's delay rather than tracking the cursor rigidly. A site is just
 * another draggable node, and its links are visual, so it moves alone.
 */
function dragBehaviour() {
  let moved = false
  return drag<SVGGElement, FNode>()
    .on('start', (event, node) => {
      zoom.claimView()
      moved = false
      // The simulation is woken here rather than in ``drag``: d3's
      // ``event.active`` is 0 only in start and end, so the textbook gate in
      // ``drag`` would never fire, and a second drag would move the pin without
      // ever ticking it into the node's position.
      if (!event.active) {
        simulation?.alphaTarget(0.3).restart()
      }
      if (node.nodeType === 'host' || node.nodeType === 'site') {
        graph.unpinDescendants(node.id, childrenOfDrawn)
      }
    })
    .on('drag', (event, node) => {
      moved = true
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
        return
      }
      if (typeof node.fx === 'number') {
        node.x = node.fx
      }
      if (typeof node.fy === 'number') {
        node.y = node.fy
      }
      // A map the user may not save lets them rearrange it as a playground,
      // and remembers none of it.
      if (!props.readonly && (node.nodeType === 'host' || node.nodeType === 'site')) {
        scheduleSave()
      }
      moved = false
    })
}

// A different map, or a different root: nothing about the old arrangement
// applies, and the next paint fits again.
watch(
  () => props.resetKey,
  () => {
    graph.clear()
    rowSpacings = new Map()
    labelWidths = new Map()
    zoom.reset()
  }
)

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

watch([() => props.topology, () => props.layout, svgEl], () => render(), { flush: 'post' })

defineExpose({
  fitView: () => zoom.fitView(),
  zoomIn: () => zoom.zoomIn(),
  zoomOut: () => zoom.zoomOut(),
  /** The area everything is drawn in, for whoever reads it back. */
  drawingArea: () => svgEl.value
})
</script>

<template>
  <div class="maps-flow-canvas">
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
        <g class="maps-flow-canvas__links" />
        <g class="maps-flow-canvas__nodes" />
      </g>
    </svg>

    <MapMarqueeBox v-if="marquee.visible.value" :rect="marquee.rect.value" :layer="4" />

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
  position: absolute;
  inset: 0;
  overflow: hidden;
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

/* While a gesture is running, hit-testing is suppressed across the whole
   subtree: without it every pointermove walks thousands of SVG descendants to
   work out a hover target the operator cannot reach mid-drag anyway. */
.maps-flow-canvas__svg--panning .maps-flow-canvas__zoom-layer {
  pointer-events: none;
}

/* The nodes and edges below are drawn by d3, so they carry no scope attribute
   of their own and have to be reached into. All of it has to be CSS: a
   pseudo-class cannot be written from script at all, the selection ring has to
   be able to win over the halo, and hiding the service nodes with one class on
   the root is the whole point — styling thousands of them one by one stutters
   mid-zoom. */
/* stylelint-disable selector-pseudo-class-no-unknown -- ``deep`` is Vue's own,
   and these elements are d3's rather than Vue's. */
:deep(.maps-flow-canvas__node:focus-visible) {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
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

/* Last of the three, so it wins at equal specificity. */
:deep(.maps-flow-canvas__node--selected > circle) {
  stroke: var(--color-corporate-green-50);
  stroke-width: 3;
}

.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__node--service),
.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__node--more),
.maps-flow-canvas__svg--low-detail :deep(.maps-flow-canvas__link--service) {
  display: none;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
