<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map nobody placed: its hosts come from a live topology query, arranged by
what depends on what.

This is the map type's own view: the states it can be in while the topology is
on its way, the search over its nodes, its zoom controls, the switch for how
much of each host's services to show, and the surfaces a node opens — the hover
card, the right-click menu, the object slide-in and the monitoring commands,
including the ones an operator sends about a whole selection at once.

The drawing itself is ``FlowCanvas``'s.

Because the nodes are not map objects, they have no entry in the shared states
store. The view therefore holds on to the node behind whatever it has open and
derives its state from the live topology, which is what keeps an open card or
slide-in ticking rather than frozen at the moment it was opened.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'

import type { CommandVerb } from '@/maps/api/ticket'
import BulkAckModal from '@/maps/map/commands/BulkAckModal.vue'
import BulkDowntimeModal from '@/maps/map/commands/BulkDowntimeModal.vue'
import ObjectCommandModals from '@/maps/map/commands/ObjectCommandModals.vue'
import { commandTargetsOf, fanOutCommand } from '@/maps/map/commands/fanOutCommand'
import { useObjectActions } from '@/maps/map/commands/useObjectActions'
import ContextMenu from '@/maps/map/components/ContextMenu.vue'
import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import type { ProblemCounts } from '@/maps/map/components/MapProblemsPill.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import MapZoomControls from '@/maps/map/components/MapZoomControls.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import { useMapObjectMenus } from '@/maps/map/composables/useMapObjectMenus'
import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import DetailDrawer from '@/maps/map/detail/DetailDrawer.vue'
import { useAggregationHint } from '@/maps/map/flow/composables/useAggregationHint'
import { useFlowSelection } from '@/maps/map/flow/composables/useFlowSelection'
import { useTopologyFeed } from '@/maps/map/flow/composables/useTopologyFeed'
import { problemScoreFromTopo } from '@/maps/map/flow/geometry'
import { needsServices } from '@/maps/map/flow/layout'
import { createFlowNodeModel } from '@/maps/map/flow/nodeModel'
import type { FNode } from '@/maps/map/flow/nodes'
import { useAuth, useMapsApis, useStates, useToast } from '@/maps/services/context'
import type { CommandTarget, MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { buildCheckmkUrl, openUrl } from '@/maps/utils/mapNavigation'
import { isProblemState } from '@/maps/utils/problemState'

import FlowBulkActionBar from './components/FlowBulkActionBar.vue'
import FlowCanvas from './components/FlowCanvas.vue'
import FlowServiceLayoutPicker from './components/FlowServiceLayoutPicker.vue'

/**
 * How many hosts are singled out as the worst-affected, and from how many hosts
 * it is worth doing — on a small map the problems are visible anyway.
 */
const WORST_COUNT = 5
const WORST_FROM = 50

const props = defineProps<{
  config: MapConfig | null
  /** Why the map could not be loaded, if it could not. */
  error: string | null
  kiosk: boolean
  /** The settings preview is not interactive. */
  preview: boolean
  checkmkUrl: string | null
  filterNeedle: string
}>()

const emit = defineEmits<{
  'update:filterNeedle': [needle: string]
  /** How much is wrong across the map, for the pill in the topbar. */
  'update:problems': [problems: ProblemCounts]
  /** What the slide-in has open, so the page around it can step aside. */
  'drawer-object': [object: MapElement | null]
}>()

const { _t } = usei18n()
const auth = useAuth()
const toast = useToast()
const { commands } = useMapsApis()
const statesStore = useStates()

const canvas = useTemplateRef<InstanceType<typeof FlowCanvas>>('canvas')

const connectionId = computed(() => props.config?.connection_id ?? '')
const flowView = computed(() => (props.config?.view.type === 'flow' ? props.config.view : null))
/** A readonly map — a bundled demo — still drags; it just remembers nothing. */
const readonly = computed(() => props.kiosk || props.preview || (props.config?.readonly ?? false))
/** A surface nobody is operating: a kiosk wall, the settings live preview. */
const unattended = computed(() => props.kiosk || props.preview)

// The map's own view settings: part of the map, but changed while reading it.
const { persist, problemsOnly, serviceLayout } = useMapViewState()

const {
  nodes: topology,
  loading,
  error: topologyError,
  fetchTopology
} = useTopologyFeed({
  connectionId: () => connectionId.value,
  flowView: () => flowView.value,
  withServices: () => needsServices(serviceLayout.value)
})

// The worst-affected hosts, given a wider halo and a glow on the map. Only
// worth doing once there are enough hosts for the problems to hide among them.
const worstHostIds = computed<Set<string>>(() => {
  if (topology.value.length < WORST_FROM) {
    return new Set()
  }
  return new Set(
    topology.value
      .map((topo) => ({ id: topo.name, score: problemScoreFromTopo(topo) }))
      .filter((scored) => scored.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, WORST_COUNT)
      .map((scored) => scored.id)
  )
})

const model = createFlowNodeModel({
  nodes: () => topology.value,
  connectionId: () => connectionId.value,
  worstHostIds: () => worstHostIds.value
})

// Owned here rather than in the canvas, like the node model: the bar that acts
// on a selection is the view's, so the view has to be able to read and clear
// it. Only the gesture that builds it is the canvas's.
const svgEl = computed<SVGSVGElement | null>(() => canvas.value?.drawingArea() ?? null)
const selection = useFlowSelection({ svgEl, mapElementFromFNode: model.mapElementFromFNode })
const selected = computed(() => selection.selectedObjects.value)

/**
 * A topology push replaces the array; a check-timing patch writes onto the
 * nodes in place and only bumps the version. Both have to make an open card or
 * slide-in look again, so both are read wherever a held node's state is.
 */
const liveTopology = computed(() => [topology.value, statesStore.topologyTimingVersion.value])

/** The live state of a node the view is holding on to. */
function liveState(node: FNode | null): ObjectState | undefined {
  void liveTopology.value
  return node ? model.objectStateFromFNode(node) : undefined
}

// --- The hover card and the right-click menu: the shared state machine, told
// how to find a flow node's state, which the states store knows nothing about.
const hoverNode = ref<FNode | null>(null)
const contextNode = ref<FNode | null>(null)
const menus = useMapObjectMenus({
  config: () => props.config,
  stateOf: (objectId) =>
    liveState([hoverNode.value, contextNode.value].find((node) => node?.id === objectId) ?? null),
  preview: () => props.preview
})

function closeMenus(): void {
  menus.close()
  hoverNode.value = null
  contextNode.value = null
}

// A click anywhere else dismisses the right-click menu.
onMounted(() => document.addEventListener('click', menus.close))
onUnmounted(() => document.removeEventListener('click', menus.close))

// --- The object slide-in.
const drawerObject = ref<MapElement | null>(null)
const drawerNode = ref<FNode | null>(null)
// Set instead of the node when the slide-in was opened from a hostname alone.
const drawerHostName = ref<string | null>(null)
const drawerState = computed(() => {
  if (drawerNode.value) {
    return liveState(drawerNode.value)
  }
  void liveTopology.value
  return drawerHostName.value ? model.hostStateByName(drawerHostName.value) : undefined
})
// An optional prop rejects an explicit undefined under exactOptionalPropertyTypes.
const drawerStateProps = computed<{ state?: ObjectState }>(() =>
  drawerState.value !== undefined ? { state: drawerState.value } : {}
)

function openDetail(object: MapElement, node: FNode): void {
  drawerObject.value = object
  drawerNode.value = node
  drawerHostName.value = null
  closeMenus()
}

function closeDetail(): void {
  drawerObject.value = null
  drawerNode.value = null
  drawerHostName.value = null
}

// Lifted so the page around the slide-in can dim its own controls and put the
// object into the breadcrumb.
watch(drawerObject, (object) => emit('drawer-object', object))

/**
 * Where a click on a node leads. A site root always opens its slide-in — there
 * is nothing else it could mean. Otherwise the map's own click action has the
 * final say, a modifier keeps the old "open it in Checkmk" behaviour, and a
 * plain click opens the slide-in rather than losing the operator's context to
 * a new tab.
 */
function onObjectClick(object: MapElement, node: FNode, event: MouseEvent | null): void {
  menus.close()
  if (node.nodeType === 'site') {
    openDetail(object, node)
    return
  }
  if (props.config?.click_action === 'none') {
    return
  }
  if (event && (event.ctrlKey || event.metaKey)) {
    const url = buildCheckmkUrl(object, props.checkmkUrl, model.objectStateFromFNode(node).site_id)
    if (url) {
      openUrl(url, '_blank')
    }
    return
  }
  openDetail(object, node)
}

function onObjectContext(object: MapElement, node: FNode, event: MouseEvent): void {
  contextNode.value = node
  menus.openContext(object, event)
}

function onObjectHover(
  object: MapElement,
  node: FNode,
  anchor: { left: number; top: number; right: number; bottom: number }
): void {
  hoverNode.value = node
  // Beside the node rather than under the pointer: a flow node is small, and
  // the card would otherwise cover the very thing it describes.
  menus.openHover(object, null, { x: anchor.right + 8, y: anchor.top, anchorRect: anchor })
}

// --- The commands about one object.
const objectActions = useObjectActions(() => props.checkmkUrl, menus.close)
const drawerCommands = objectActions.drawerHandlers(() => drawerObject.value)

// --- The commands about a whole selection.
// A command sent to fifty hosts at once is still a command: it needs the same
// permission the single-object ones ask for, and a surface nobody is operating —
// a kiosk, the settings preview — sends none at all.
const canBulk = (verb: CommandVerb): boolean => !unattended.value && auth.mayCommand(verb)
const canBulkAcknowledge = computed(() => canBulk('acknowledge'))
const canBulkDowntime = computed(() => canBulk('schedule_downtime'))
const canBulkForceCheck = computed(() => canBulk('force_check'))
const canBulkAnything = computed(
  () => canBulkAcknowledge.value || canBulkDowntime.value || canBulkForceCheck.value
)
const bulkAckTargets = ref<CommandTarget[] | null>(null)
/** How many of the picked have nothing to acknowledge, and are left out. */
const bulkAckSkipped = ref(0)
const bulkDowntimeTargets = ref<CommandTarget[] | null>(null)
/** What the audit trail names these as having been picked from. */
const selectionOrigin = computed(() => props.config?.alias || props.config?.name || '')

function closeBulk(sent: boolean): void {
  bulkAckTargets.value = null
  bulkDowntimeTargets.value = null
  // Dismissing the dialog must leave the selection alone: it was assembled by
  // hand, node by node, and there is no way to get it back.
  if (sent) {
    selection.clear()
    statesStore.refreshAfterCommand()
  }
}

/** The state a command about this node is judged by: a host's own, not its services'. */
function commandedState(node: FNode): string | undefined {
  if (node.nodeType === 'service') {
    return liveState(node)?.state
  }
  // A "+N more" bubble is commanded as the host it hangs off.
  return model.hostStateByName(node.nodeType === 'more' ? (node.hostId ?? '') : node.id)?.state
}

/**
 * Checkmk refuses to acknowledge an object that has no problem, so only the
 * picked ones that have one are offered.
 */
function onBulkAcknowledge(): void {
  const problems = selection.selectedNodes.value.filter((node) =>
    isProblemState(commandedState(node))
  )
  const targets = commandTargetsOf(problems.map(model.mapElementFromFNode))
  bulkAckSkipped.value = commandTargetsOf(selected.value).length - targets.length
  bulkAckTargets.value = targets
}

/**
 * A forced check asks for nothing and confirms nothing, so it is sent straight
 * away rather than through a modal — reported once for the whole selection,
 * not once per host.
 */
async function onBulkForceCheck(): Promise<void> {
  const targets = commandTargetsOf(selected.value)
  selection.clear()
  const result = await fanOutCommand(
    targets,
    (target) =>
      target.service
        ? commands.forceCheckService(target.host, target.service, target.site)
        : commands.forceCheckHost(target.host, target.site),
    { what: 'force check' }
  )
  if (result.failed.length) {
    toast.error(
      _t('Force check failed for %{failed} of %{total}', {
        failed: result.failed.length,
        total: result.total
      })
    )
  } else if (result.succeeded > 0) {
    toast.success(_t('Force check scheduled for %{count}', { count: result.succeeded }))
  }
  statesStore.refreshAfterCommand()
}

// --- What the operator is told about the map as a whole.
//
// With the services switched off there is no per-host sign of a service
// problem, so a map full of them still shows nothing but green dots. The
// counts are aggregated here and shown in the topbar instead. Unknown is
// counted in the total — an unknown-only map should still say something — but
// only the more actionable two are named.
const problems = computed<ProblemCounts>(() => {
  let critical = 0
  let warning = 0
  let unknown = 0
  let hostsWithProblems = 0
  for (const topo of topology.value) {
    const summary = topo.services_summary
    if (!summary) {
      continue
    }
    if (summary.critical || summary.warning || summary.unknown) {
      hostsWithProblems += 1
    }
    critical += summary.critical
    warning += summary.warning
    unknown += summary.unknown
  }
  return { critical, warning, hostsWithProblems, total: critical + warning + unknown }
})

watch(problems, (value) => emit('update:problems', value), { immediate: true })

// How many hosts the backend left aggregated because it did not count them
// among the worst. Only worth saying while the layout would have shown their
// services, which is why they are a ring instead.
const aggregatedHosts = computed(() => {
  const total = topology.value.length
  const omitted = topology.value.filter((topo) => topo.services_omitted).length
  return { total, shown: total - omitted, omitted }
})

const { dismissed: hintDismissed, dismiss: dismissHint } = useAggregationHint(
  () => auth.user.value?.user_id
)

const showsAggregationHint = computed(
  () =>
    aggregatedHosts.value.omitted > 0 &&
    needsServices(serviceLayout.value) &&
    (props.preview || !hintDismissed.value)
)

// The hosts this map draws, so a parent or child in the slide-in's topology
// section can be a jump onto the map rather than only a link into Checkmk.
const selectableHosts = computed(() => topology.value.map((topo) => topo.name))

/**
 * A jump from the slide-in's topology section. A flow map's nodes are not map
 * objects, so the slide-in is handed a stand-in built from the hostname.
 */
function onSelectHost(hostName: string): void {
  if (!topology.value.some((topo) => topo.name === hostName)) {
    return
  }
  drawerObject.value = { id: hostName, type: 'host', x: 0, y: 0, host_name: hostName } as MapElement
  drawerNode.value = null
  drawerHostName.value = hostName
  closeMenus()
}

/** Changes when this is a different map, or looks at a different root. */
const resetKey = computed(() => {
  const view = flowView.value
  return [
    connectionId.value,
    view?.root ?? '',
    view?.child_layers ?? '',
    view?.parent_layers ?? ''
  ].join('|')
})

// A different root means a different set of hosts. The previous ones are hidden
// while the new topology is on its way, and anything opened on or picked from
// them would be about hosts this map no longer shows — the view is reused from
// one map to the next, so a stale selection would otherwise keep driving the
// command bar.
watch(resetKey, () => {
  closeMenus()
  closeDetail()
  selection.clear()
  void fetchTopology({ reset: true })
})

// Which services the backend has to send depends on the layout. Over the live
// stream the topology arrives with them regardless, so the switch is then a
// pure matter of drawing and the canvas handles it alone.
watch(serviceLayout, () => {
  if (!statesStore.streamAvailable.value) {
    void fetchTopology()
  }
})
</script>

<template>
  <div class="maps-flow-map-view">
    <MapPlaceholder v-if="error" :message="error" variant="error" />

    <template v-else-if="config">
      <MapPlaceholder
        v-if="!connectionId"
        :message="_t('No connection configured for this map.')"
        variant="empty"
      />
      <div v-else-if="loading" class="maps-flow-map-view__loading">
        <CmkLoading />
      </div>
      <!-- Only when there is nothing to fall back on. A failed poll while a
           topology is already drawn is reported over the map instead: tearing
           the canvas down would cost the arrangement, the zoom and the
           selection for what is usually one missed request. -->
      <MapPlaceholder
        v-else-if="topologyError && !topology.length"
        :message="topologyError"
        variant="error"
      />

      <template v-else>
        <FlowCanvas
          ref="canvas"
          :topology="topology"
          :model="model"
          :selection="selection"
          :layout="serviceLayout"
          :connection-id="connectionId"
          :saved-positions="flowView?.positions ?? {}"
          :clickable="config.click_action !== 'none'"
          :readonly="readonly"
          :preview="preview"
          :filter-needle="filterNeedle"
          :problems-only="problemsOnly"
          :reset-key="resetKey"
          @object-click="onObjectClick"
          @object-context="onObjectContext"
          @object-hover="onObjectHover"
          @object-hover-leave="menus.hover.scheduleClose()"
          @positions-changed="persist({ positions: $event })"
        />

        <div v-if="topologyError && !preview" class="maps-flow-map-view__stale">
          <CmkAlertBox variant="warning" size="small">
            {{ _t('Topology update failed — showing the last one that arrived') }}
          </CmkAlertBox>
        </div>

        <MapSearch
          v-if="!drawerObject && !preview"
          :model-value="filterNeedle"
          :exclude-prefixes="['hg', 'sg']"
          @update:model-value="emit('update:filterNeedle', $event)"
        >
          <template #trailing>
            <ProblemsOnlyToggle
              v-model="problemsOnly"
              :title="_t('Show only hosts with problems')"
            />
          </template>
        </MapSearch>

        <MapZoomControls
          v-if="!preview"
          :can-fit="topology.length > 0"
          @zoom-in="canvas?.zoomIn()"
          @zoom-out="canvas?.zoomOut()"
          @fit="canvas?.fitView()"
        />

        <div v-if="showsAggregationHint" class="maps-flow-map-view__hint">
          <span>
            {{
              preview
                ? _t('Services shown for %{shown} of %{total} hosts', aggregatedHosts)
                : _t(
                    'Showing service detail for the top %{shown} of %{total} most affected hosts — others are aggregated as donuts',
                    aggregatedHosts
                  )
            }}
          </span>
          <CmkIconButton
            v-if="!preview"
            name="close"
            size="small"
            class="maps-flow-map-view__hint-dismiss"
            :title="_t('Dismiss this hint')"
            :aria-label="_t('Dismiss this hint')"
            @click="dismissHint"
          />
        </div>

        <FlowBulkActionBar
          v-if="selected.length > 0 && canBulkAnything"
          :count="selected.length"
          :can-acknowledge="canBulkAcknowledge"
          :can-downtime="canBulkDowntime"
          :can-force-check="canBulkForceCheck"
          @acknowledge="onBulkAcknowledge"
          @schedule-downtime="bulkDowntimeTargets = commandTargetsOf(selected)"
          @force-check="void onBulkForceCheck()"
          @clear="selection.clear()"
        />

        <FlowServiceLayoutPicker v-if="!drawerObject && !preview" v-model="serviceLayout" />
      </template>

      <HoverMenu
        v-if="menus.hover.hover.visible && menus.hover.hover.object"
        :object="menus.hover.hover.object"
        :state="menus.hover.state.value"
        :x="menus.hover.hover.x"
        :y="menus.hover.hover.y"
        :anchor-rect="menus.hover.hover.anchorRect"
        :connection-id="connectionId"
        :checkmk-url="checkmkUrl"
        :template="menus.hoverTemplate.value"
        @card-enter="menus.hover.cancelClose()"
        @card-leave="menus.hover.scheduleClose()"
      />

      <ContextMenu
        v-if="menus.context.visible && menus.context.object"
        :object="menus.context.object"
        v-bind="menus.contextState.value"
        :x="menus.context.x"
        :y="menus.context.y"
        :checkmk-url="checkmkUrl"
        :template="menus.contextTemplate.value"
        @close="menus.close()"
      />

      <DetailDrawer
        :object="drawerObject"
        v-bind="drawerStateProps"
        :checkmk-url="checkmkUrl"
        :connection-id="connectionId"
        :selectable-hosts="selectableHosts"
        :unattended="unattended"
        v-on="drawerCommands"
        @close="closeDetail"
        @select-host="onSelectHost"
      />
    </template>

    <MapPlaceholder v-else :message="_t('Map not found')" variant="empty" />

    <ObjectCommandModals :actions="objectActions" :checkmk-url="checkmkUrl" />

    <BulkAckModal
      v-if="bulkAckTargets"
      :origin="selectionOrigin"
      :targets="bulkAckTargets"
      :skipped="bulkAckSkipped"
      @close="closeBulk"
    />
    <BulkDowntimeModal
      v-if="bulkDowntimeTargets"
      :origin="selectionOrigin"
      :targets="bulkDowntimeTargets"
      @close="closeBulk"
    />
  </div>
</template>

<style scoped>
.maps-flow-map-view {
  position: relative;
  flex: 1 1 0%;
  overflow: hidden;
  background: var(--ux-theme-1);
}

.maps-flow-map-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* Top centre: the zoom controls hold the left corner, the search the right. */
.maps-flow-map-view__stale {
  position: absolute;
  top: var(--dimension-5);
  left: 50%;
  z-index: 6;
  max-width: min(60%, 520px);
  transform: translateX(-50%);
}

.maps-flow-map-view__hint {
  position: absolute;
  bottom: var(--dimension-6);
  left: 56px;
  z-index: 6;
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  max-width: min(60%, 520px);
  padding: 4px 4px 4px 10px;
  color: var(--font-color);
  font-size: var(--font-size-normal);
  text-align: left;
  background: var(--maps-map-view-glass);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  backdrop-filter: blur(6px);
  pointer-events: none;
}

/* The hint itself is not in the way of the map; only its dismissal is. */
.maps-flow-map-view__hint-dismiss {
  pointer-events: auto;
}
</style>
