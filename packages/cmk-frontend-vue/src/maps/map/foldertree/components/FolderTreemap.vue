<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The folder tree as a treemap: every folder a card, every host a chip, sized so
the whole site fits on one screen and the problems are the first thing on it.

D3 owns the tiles, because a relayout has to animate thousands of them; this
component owns the frame, the lifecycle and what a tile answers to. It relays
out only when the visible set actually changed -- a live tick that only moves a
state repaints in place, which is the difference between a map that hums along
under a state stream and one that reshuffles every few seconds.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { useTheme } from 'cmk-ui-library/lib/useTheme'
import { computed, ref, useTemplateRef, watch } from 'vue'

import { useD3Cleanup } from '@/maps/map/composables/useD3Cleanup'
import { useStates } from '@/maps/services/context'
import type { FolderTreeNode } from '@/maps/types/api'

import type { FolderExpansion } from '../composables/useFolderExpansion'
import { type FolderQuery, hostsMatchedByAncestor, selfMatches, visibleServices } from '../filter'
import {
  type Tile,
  aggregatedChildren,
  filteredRoot,
  folderAtPath,
  layoutTreemap,
  tileSignature,
  visibleTiles
} from '../treemapLayout'
import { drawTiles, recolorTiles } from '../treemapPaint'
import { tileText } from '../treemapText'

/** The light theme's name, whose stage the tile tints have to allow for. */
const LIGHT_THEME = 'facelift'

const props = defineProps<{
  /** The tree to draw, as the view named it. */
  root: FolderTreeNode
  query: FolderQuery
  expansion: FolderExpansion
  /** Whether hosts can be drilled into at all. */
  showServices: boolean
  servicesByHost: Record<string, FolderTreeNode[]>
  serviceLoading: ReadonlySet<string>
  serviceError: ReadonlySet<string>
}>()

const emit = defineEmits<{
  /** A leaf was picked. `host` names the host a service runs on, else null. */
  select: [host: string | null, node: FolderTreeNode]
  /** A host was opened, so its services have to be fetched. */
  'expand-host': [FolderTreeNode]
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const { _t, _tn } = usei18n()
const states = useStates()
const { theme } = useTheme()

const svgEl = useTemplateRef<SVGSVGElement>('svgEl')
const stageEl = useTemplateRef<HTMLDivElement>('stageEl')
const tipEl = useTemplateRef<HTMLDivElement>('tipEl')

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null)

let stage = { width: 0, height: 0 }
let lastSignature = ''

// The services of a host that survive the filter -- the same set the list shows
// under it, since both ask the shared filter with the same answer to "did this
// host match", its own name or a folder above it.
const matchedByAncestor = computed(() => hostsMatchedByAncestor(props.root, props.query.terms))

const hostMatched = (host: FolderTreeNode): boolean =>
  matchedByAncestor.value.has(host.path) || selfMatches(host, props.query.terms)

const servicesOf = (host: FolderTreeNode): FolderTreeNode[] =>
  visibleServices(
    host.title,
    props.servicesByHost[host.title] ?? [],
    props.query,
    hostMatched(host)
  )

const drawnRoot = computed(() => filteredRoot(props.root, props.query, servicesOf))

/** A node the operator can drill into: a folder with something in it, or -- when
 *  services are shown -- a host. */
const canExpand = (node: FolderTreeNode): boolean =>
  node.kind === 'folder' ? !node.is_empty : node.kind === 'host' && props.showServices

// While a search is running the drawn root is already pruned to the paths
// leading to matches, so every folder on the way down opens: the match shows
// rather than hiding inside a collapsed tile. The operator's own expansion is
// left alone and takes over again once the search is cleared. Problems-only
// keeps the collapsed overview, being a filter rather than a lookup.
function isOpen(node: FolderTreeNode): boolean {
  const searching = props.query.terms.length > 0
  if (node.kind === 'folder') {
    return node.children.length > 0 && (searching || props.expansion.expanded.has(node.path))
  }
  if (node.kind !== 'host') {
    return false
  }
  // A host is open only once its services are actually there; until then it
  // stays a chip, and the click that opened it started the fetch. (The list
  // opens it either way -- it has a row to say "loading" in, a tile does not.)
  if (!props.showServices || !props.servicesByHost[node.title]?.length) {
    return false
  }
  if (servicesOf(node).length === 0) {
    return false
  }
  // A host that survived the search only through a matching service opens to
  // reveal it; one matched by its own name stays a chip. (The list draws the
  // same line, on the host's own name rather than on a folder hit above it.)
  if (searching && !selfMatches(node, props.query.terms)) {
    return true
  }
  return props.expansion.expanded.has(node.path)
}

const childrenOf = (node: FolderTreeNode): FolderTreeNode[] =>
  node.kind === 'host'
    ? servicesOf(node)
    : aggregatedChildren(node, props.query, (count) => `✓ ${count} ${_t('OK')}`)

const text = computed(() =>
  tileText({
    _t,
    _tn,
    canExpand,
    serviceLoading: props.serviceLoading,
    serviceError: props.serviceError
  })
)

function layout(): Tile | null {
  return layoutTreemap({ root: drawnRoot.value, ...stage, isOpen, childrenOf })
}

function activate(tile: Tile): void {
  const node = tile.data
  if (!canExpand(node)) {
    if (node.kind === 'host') {
      emit('select', null, node)
    } else if (node.kind === 'service') {
      emit('select', tile.parent?.data.title ?? '', node)
    }
    return
  }
  const wasOpen = props.expansion.expanded.has(node.path)
  props.expansion.toggle(node.path)
  if (node.kind === 'host' && !wasOpen) {
    emit('expand-host', node)
  }
}

function showTip(event: MouseEvent, tile: Tile): void {
  const bounds = stageEl.value?.getBoundingClientRect()
  if (!bounds) {
    return
  }
  tip.value = {
    x: event.clientX - bounds.left + 12,
    y: event.clientY - bounds.top + 12,
    ...text.value.tooltip(tile)
  }
}

const handlers = {
  activate,
  context: (tile: Tile, x: number, y: number) => {
    // Real folders only -- the synthetic "all OK" bundle has no folder behind it.
    if (tile.data.kind !== 'folder' || tile.data.ok_group) {
      return
    }
    // Under a filter the tile holds a pruned copy, whose children are only the
    // hosts that matched. The menu acts on the folder as a whole, so it is
    // handed the node out of the real tree -- the one the list emits.
    emit('ctx-folder', folderAtPath(props.root, tile.data.path) ?? tile.data, x, y)
  },
  hover: showTip,
  hoverEnd: () => {
    tip.value = null
  }
}

function paint(animate: boolean): void {
  const svg = svgEl.value
  const laid = layout()
  if (!svg || !laid) {
    return
  }
  const tiles = visibleTiles(laid)
  const options = { text: text.value, light: theme.value === LIGHT_THEME }
  const signature = tileSignature(tiles)
  // The same tiles came back at the same sizes, so only the colours can have
  // changed -- repainting in place leaves an in-flight layout transition alone.
  if (animate && signature === lastSignature) {
    recolorTiles(svg, tiles, options)
    return
  }
  lastSignature = signature
  drawTiles(svg, tiles, { ...options, ...stage, animate, handlers })
}

// Keep the tooltip inside the stage. Its real size is only known once it is
// rendered (it does not wrap, so it can be wide), so it flips to the other side
// of the cursor when it would overflow. `post` runs after the DOM patch, so the
// element measured is the one holding the current text.
watch(
  tip,
  () => {
    const element = tipEl.value
    if (!tip.value || !element || !stage.width || !stage.height) {
      return
    }
    const width = element.offsetWidth
    const height = element.offsetHeight
    const x =
      tip.value.x + width + 4 > stage.width ? Math.max(4, tip.value.x - width - 24) : tip.value.x
    const y =
      tip.value.y + height + 4 > stage.height ? Math.max(4, tip.value.y - height - 24) : tip.value.y
    element.style.left = `${x}px`
    element.style.top = `${y}px`
  },
  { flush: 'post' }
)

// Everything the drawing depends on: the tree and its live states, the filter,
// what is open, and the lazily-fetched services arriving or changing state.
// Each source is O(1) to evaluate -- Vue re-evaluates all of them whenever any
// one of them fires, and the state tick fires every few seconds.
watch(
  [
    drawnRoot,
    () => states.folderTreeVersion.value,
    () => props.expansion.version.value,
    () => props.servicesByHost,
    () => props.serviceLoading.size,
    () => props.serviceError.size,
    theme
  ],
  () => paint(true),
  { flush: 'post' }
)

useResizeObserver((entries) => {
  const rect = entries[0]?.contentRect
  if (!rect) {
    return
  }
  const changed = Math.abs(rect.width - stage.width) > 1 || Math.abs(rect.height - stage.height) > 1
  stage = { width: rect.width, height: rect.height }
  if (changed) {
    // A resize is not a change of content: the tiles jump to their new geometry
    // rather than animating there.
    paint(false)
  }
}).observe(stageEl)

useD3Cleanup(svgEl)
</script>

<template>
  <div ref="stageEl" class="maps-folder-treemap">
    <svg ref="svgEl" class="maps-folder-treemap__stage" />
    <div
      v-if="tip"
      ref="tipEl"
      class="maps-folder-treemap__tip"
      :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
    >
      <span class="maps-folder-treemap__tip-dot" :style="{ background: tip.color }" />
      <strong>{{ tip.title }}</strong>
      <span class="maps-folder-treemap__tip-meta">{{ tip.meta }}</span>
    </div>
    <div v-if="!drawnRoot.children.length" class="maps-folder-treemap__empty">
      {{ _t('Nothing to show here.') }}
    </div>
  </div>
</template>

<style scoped>
.maps-folder-treemap {
  position: relative;
  flex: 1;
  min-height: 0;
}

.maps-folder-treemap__stage {
  display: block;
  width: 100%;
  height: 100%;
}

/* stylelint-disable selector-pseudo-class-no-unknown -- d3 owns the tiles, so
   their styles have to reach past this component's own markup. */
.maps-folder-treemap__stage :deep(.maps-folder-treemap__cell:focus-visible) {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: -2px;
}

.maps-folder-treemap__stage :deep(.maps-folder-treemap__label),
.maps-folder-treemap__stage :deep(.maps-folder-treemap__mark) {
  fill: var(--font-color);
  font-weight: var(--font-weight-bold);
  paint-order: stroke;
  pointer-events: none;
  stroke: var(--bg-glass);
  stroke-width: 2.5px;
  stroke-linejoin: round;
}

.maps-folder-treemap__stage :deep(.maps-folder-treemap__label) {
  font-size: var(--font-size-normal);
}

.maps-folder-treemap__stage :deep(.maps-folder-treemap__mark) {
  font-size: 11px;
  font-weight: var(--font-weight-default);
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.maps-folder-treemap__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-8);
  font-size: 13px;
  color: var(--font-color-dimmed);
  text-align: center;

  /* Never swallows a click on the tiles beneath it. */
  pointer-events: none;
}

.maps-folder-treemap__tip {
  position: absolute;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 9px;
  font-size: var(--font-size-normal);
  color: var(--font-color);
  white-space: nowrap;
  background: var(--bg-glass);
  border: 1px solid var(--default-border-color);
  border-radius: 6px;
  box-shadow: 0 2px 10px rgb(0 0 0 / 18%);
  pointer-events: none;
}

.maps-folder-treemap__tip-dot {
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border-radius: 50%;
}

.maps-folder-treemap__tip-meta {
  color: var(--font-color-dimmed);
}
</style>
