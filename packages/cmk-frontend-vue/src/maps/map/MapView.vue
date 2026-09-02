<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The page a map is read on: the chrome around the drawing, the map's own
lifecycle, and which map type gets to draw.

The view is reused rather than re-created when the map changes -- a rotation or
a click on a map object swaps the name under the same component -- so the
lifecycle is keyed on the name (``useMapLifecycle``) and not on mount.

This is also where the map's own design values are declared, on the view root,
so every painter below inherits one set of them.

Only static maps are drawn so far. The other map types and the editing UI
arrive in the commits that follow this one.
-->
<script setup lang="ts">
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref, useTemplateRef, watch } from 'vue'

import AckModal from '@/maps/map/commands/AckModal.vue'
import BulkAckModal from '@/maps/map/commands/BulkAckModal.vue'
import CommentModal from '@/maps/map/commands/CommentModal.vue'
import DowntimeModal from '@/maps/map/commands/DowntimeModal.vue'
import RemoveDowntimeModal from '@/maps/map/commands/RemoveDowntimeModal.vue'
import { useObjectActions } from '@/maps/map/commands/useObjectActions'
import MapKioskExit from '@/maps/map/components/MapKioskExit.vue'
import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapViewTopbar from '@/maps/map/components/MapViewTopbar.vue'
import { useMapEditor } from '@/maps/map/composables/useMapEditor'
import { useMapFullscreen } from '@/maps/map/composables/useMapFullscreen'
import { useMapLifecycle } from '@/maps/map/composables/useMapLifecycle'
import { provideMapPalette } from '@/maps/map/composables/useMapPalette'
import { useMapRotation } from '@/maps/map/composables/useMapRotation'
import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import { usePreviewBridge } from '@/maps/map/composables/usePreviewBridge'
import DetailDrawer from '@/maps/map/detail/DetailDrawer.vue'
import StaticMapView from '@/maps/map/static/StaticMapView.vue'
import { useAuth, useConnections, useMaps, useNavigation, useStates } from '@/maps/services/context'
import type { BulkAckTarget, MapElement, ObjectState } from '@/maps/types/api'
import { resolveCheckmkUrl } from '@/maps/utils/deploymentBase'
import { objectDisplayName } from '@/maps/utils/dropdownOptions'
import { buildCheckmkUrl, openUrl } from '@/maps/utils/mapNavigation'
import { newMapElement } from '@/maps/utils/model'

const { _t } = usei18n()
const nav = useNavigation()
const auth = useAuth()
const mapsStore = useMaps()
const statesStore = useStates()
const connectionsStore = useConnections()

const mapName = computed(() => nav.state.name ?? '')
const isKiosk = computed(() => nav.state.kiosk)
const isPreview = computed(() => nav.state.preview)

const { openKioskInNewTab, exitFullscreen } = useMapFullscreen(mapName, isKiosk)

const mapConfig = computed(() => mapsStore.currentMap.value)

// Whether the current user may edit *this* map: the per-map pagetype
// capability the backend stamps on the map-list entry (built-ins and
// unauthorized foreign maps are read-only -- admin rights ride in via the
// "edit foreign maps" permission, not via configure/admin status).
const canEdit = computed(
  () => mapsStore.maps.value.find((b) => b.name === mapName.value)?.can_edit === true
)

// Every other map type draws itself; until its own commit lands, saying so
// beats rendering it as something it is not.
const isStatic = computed(() => (mapConfig.value?.view.type ?? 'static') === 'static')

// Top-right search bar over the map's objects. Reset on a map switch, so a
// needle typed on the previous map does not hide the new one's objects.
const mapFilterNeedle = ref('')
watch(mapName, () => {
  mapFilterNeedle.value = ''
})

const { problemsOnly } = useMapViewState()

const isLoading = computed(
  () => mapsStore.loading.value || (statesStore.initialLoad.value && !mapsStore.error.value)
)

const checkmkUrl = computed(() => {
  const bid = mapConfig.value?.connection_id
  const connUrl = bid
    ? (connectionsStore.connections.value.find((b) => b.id === bid)?.checkmk_url ?? null)
    : null
  return connUrl ?? resolveCheckmkUrl()
})

const editor = useMapEditor()

const { rotationCountdown, rotationPaused, stopRotation, scheduleRotation, toggleRotationPause } =
  useMapRotation(mapName, editor.editMode)

// The map's own design values, and the resolved palette every painter that
// works outside CSS reads. Declared on the view root so everything below
// inherits them.
const root = useTemplateRef<HTMLElement>('root')
provideMapPalette(root)

// ---- The object slide-in, and the commands sent from it ----

const detailDrawerObject = ref<MapElement | null>(null)
// Drilldown targets (BI aggregation leaves) never enter the SSE states store,
// so the drawer has no live state to key off their synthesized ids. Capture
// the clicked node's state here so the drawer still shows status/output/age.
const drawerSeedState = ref<ObjectState | null>(null)
const detailDrawerState = computed(() => {
  const obj = detailDrawerObject.value
  if (!obj) {
    return undefined
  }
  const live = statesStore.states.value[obj.id]
  if (live) {
    return live
  }
  if (drawerSeedState.value?.object_id === obj.id) {
    return drawerSeedState.value
  }
  return undefined
})

const detailActions = useObjectActions(() => checkmkUrl.value)

function openDetail(obj: MapElement) {
  // A line is a visual relation between two endpoints, but in monitoring
  // terms it represents either the host or the host's service (whichever
  // is configured). Drawer logic keys off `type` to fetch state and
  // render the right tabs, so expose the line as its underlying
  // host/service for the drawer's purposes.
  if (obj.type === 'line' && obj.host_name) {
    detailDrawerObject.value = {
      ...obj,
      type: obj.service_description ? 'service' : 'host'
    }
  } else {
    detailDrawerObject.value = obj
  }
}

function closeDetail() {
  detailDrawerObject.value = null
  drawerSeedState.value = null
}

// All host MapElements on this map, keyed by hostname so the Drawer's
// topology section can decide whether a parent/child entry can highlight on
// the map (vs. just linking to Checkmk).
const selectableHostNames = computed(() =>
  (mapConfig.value?.objects ?? [])
    .filter((o) => o.type === 'host' && o.host_name)
    .map((o) => o.host_name as string)
)

function onSelectHost(
  hostName: string,
  serviceDescription?: string | null,
  seed?: Omit<ObjectState, 'object_id'> | null
) {
  // Prefer a real map-object so toolbar actions (ack/downtime) bind to the
  // operator's curated entry. Fall back to a synthesised object so members
  // discovered via the hostgroup drawer (often not placed on the map)
  // still open in the same slidein -- the parent state cycle lifts onto the
  // standard host/service-detail-fetch watch automatically.
  const objs = mapConfig.value?.objects ?? []
  const real = objs.find((o) => {
    if (o.type === 'service') {
      return (
        o.host_name === hostName &&
        (serviceDescription ? o.service_description === serviceDescription : true)
      )
    }
    return o.type === 'host' && o.host_name === hostName
  })
  if (real) {
    detailDrawerObject.value = real
    return
  }
  const transientId = serviceDescription
    ? `transient:${hostName};${serviceDescription}`
    : `transient:${hostName}`
  // Transient objects have no SSE state entry; a caller-provided seed (e.g.
  // a BI leaf's node state) keeps the drawer's status pane populated.
  if (seed) {
    drawerSeedState.value = { ...seed, object_id: transientId }
  }
  detailDrawerObject.value = newMapElement({
    id: transientId,
    type: serviceDescription ? 'service' : 'host',
    host_name: hostName,
    ...(serviceDescription ? { service_description: serviceDescription } : {}),
    z: 0
  })
}

function onDetailAck() {
  detailActions.handlers.acknowledge(detailDrawerObject.value)
}
function onDetailRemoveAck() {
  void detailActions.handlers.removeAck(detailDrawerObject.value)
}
function onDetailDowntime() {
  detailActions.handlers.scheduleDowntime(detailDrawerObject.value)
}
function onDetailRemoveDowntime() {
  void detailActions.handlers.removeDowntime(detailDrawerObject.value)
}
function onDetailForceCheck() {
  void detailActions.handlers.forceCheck(detailDrawerObject.value)
}
function onDetailAddComment() {
  detailActions.handlers.addComment(detailDrawerObject.value)
}
function onDetailToggleNotifications(enable: boolean) {
  void detailActions.handlers.toggleNotifications(detailDrawerObject.value, enable)
}

/**
 * Bulk-acknowledge contributing leaves of a BI aggregation. Opens the
 * BulkAckModal -- that previews the targets, lets the operator review/edit
 * the comment (pre-filled with "Bulk-ack: <aggregation_id>" so audit logs
 * trace back to the originating aggregation), and runs the per-leaf ack
 * loop with progress feedback. Firing N acks straight off a click would be
 * risky for a misclick, since they have no atomic undo.
 */
function onDetailBulkAcknowledge(targets: BulkAckTarget[]) {
  if (!checkmkUrl.value || !targets.length) {
    return
  }
  const obj = detailDrawerObject.value
  const aggregationId = obj?.aggregation_id ?? obj?.id ?? 'unknown'
  bulkAckModal.value = { aggregationId, targets }
}

const bulkAckModal = ref<{
  aggregationId: string
  targets: BulkAckTarget[]
} | null>(null)

// A bulk ack's effect shows up in monitoring a moment later, so closing it
// asks the state stream for a fresh picture -- the same thing the
// single-object modals do via ``useObjectActions``.
function closeBulkAckModal() {
  bulkAckModal.value = null
  statesStore.refreshAfterCommand()
}

// The map itself stays the breadcrumb's last level until the slide-in is
// open: then the map name links back to the bare map.
const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
  const mapTitle = mapConfig.value?.alias || mapName.value
  const items: BreadcrumbItem[] = [{ title: _t('Maps'), link: nav.href({ view: 'home' }) }]
  if (detailDrawerObject.value) {
    items.push({ title: mapTitle, link: nav.href({ view: 'map', name: mapName.value }) })
    items.push({ title: objectDisplayName(detailDrawerObject.value, _t), link: null })
  } else {
    items.push({ title: mapTitle, link: null })
  }
  return items
})

/**
 * What a click on an object leads to. The object's own link wins, a map object
 * navigates, Ctrl+Click leaves for Checkmk -- and a plain click opens the
 * object's slide-in.
 */
function onObjectClick(obj: MapElement, event?: MouseEvent) {
  if (editor.editMode.value) {
    const additive = !!(event && (event.shiftKey || event.ctrlKey || event.metaKey))
    editor.selectObject(obj.id, additive)
    return
  }
  if (mapConfig.value?.click_action === 'none') {
    return
  }
  if (obj.url) {
    openUrl(obj.url, obj.url_target || '_blank')
    return
  }
  if (obj.type === 'map' && obj.map_name) {
    nav.navigate({ view: 'map', name: obj.map_name })
    return
  }
  if (event && (event.ctrlKey || event.metaKey)) {
    const cmkUrl = buildCheckmkUrl(obj, checkmkUrl.value, statesStore.getState(obj.id)?.site_id)
    if (cmkUrl) {
      openUrl(cmkUrl, '_blank')
    }
    return
  }
  // Decorative objects without a monitored target have nothing to show in
  // the drawer. Click is a no-op rather than an empty drawer.
  if (!objectHasMonitoringTarget(obj)) {
    return
  }
  openDetail(obj)
}

function objectHasMonitoringTarget(obj: MapElement): boolean {
  switch (obj.type) {
    case 'host':
    case 'service':
    case 'line':
      return Boolean(obj.host_name)
    case 'hostgroup':
    case 'servicegroup':
      return Boolean(obj.group_name)
    case 'dyngroup':
      return Boolean(obj.object_filter)
    case 'aggregation':
      return Boolean(obj.aggregation_id)
    default:
      return false
  }
}

useMapLifecycle({
  mapName: () => mapName.value,
  onMapChanged: () => editor.resetForNewMap(),
  rotation: { stop: stopRotation, schedule: scheduleRotation }
})

usePreviewBridge({ preview: () => isPreview.value })

onMounted(() => {
  if (auth.canConfigure || auth.canCreateMaps) {
    void connectionsStore.fetch()
  }
  // The map list carries the per-map edit capability; loading it even on a
  // direct deep link is what gives a non-admin editor their edit affordances.
  if (mapsStore.maps.value.length === 0) {
    void mapsStore.fetchMaps()
  }
})
</script>

<template>
  <div ref="root" class="maps-map-view" role="region" :aria-label="_t('Map view')">
    <MapViewTopbar
      v-if="!isKiosk && !isPreview"
      :connected="statesStore.connected.value"
      :readonly="mapConfig?.readonly === true"
      :editing="editor.editMode.value"
      :rotation-seconds="mapConfig && mapConfig.rotation_interval > 0 ? rotationCountdown : 0"
      :rotation-paused="rotationPaused"
      :dimmed="!!detailDrawerObject"
      @toggle-rotation="toggleRotationPause"
      @open-full-screen="openKioskInNewTab"
    >
      <template #breadcrumb>
        <CmkBreadcrumb :items="breadcrumbItems" />
      </template>
    </MapViewTopbar>

    <MapKioskExit v-if="isKiosk" @exit="exitFullscreen" />

    <!-- The map area. The slide-ins that open over a map sit inside it, so
         they stay under the topbar. -->
    <div class="maps-map-view__shell">
      <div v-if="isLoading" class="maps-map-view__loading">
        <CmkLoading />
        <span>{{ _t('Loading map…') }}</span>
      </div>

      <MapPlaceholder
        v-if="!isStatic"
        :message="_t('This map type cannot be shown yet')"
        variant="empty"
      />
      <StaticMapView
        v-else
        v-model:filter-needle="mapFilterNeedle"
        v-model:problems-only="problemsOnly"
        :config="mapConfig"
        :states="statesStore.states.value"
        :editor="editor"
        :error="mapsStore.error.value"
        :can-edit="canEdit"
        :kiosk="isKiosk"
        :preview="isPreview"
        :checkmk-url="checkmkUrl"
        @object-click="onObjectClick"
      />

      <DetailDrawer
        :object="detailDrawerObject"
        :state="detailDrawerState"
        :checkmk-url="checkmkUrl"
        :connection-id="detailDrawerObject?.connection_id ?? mapConfig?.connection_id ?? null"
        :selectable-hosts="selectableHostNames"
        :unattended="isKiosk || isPreview"
        @close="closeDetail"
        @acknowledge="onDetailAck"
        @remove-ack="onDetailRemoveAck"
        @schedule-downtime="onDetailDowntime"
        @remove-downtime="onDetailRemoveDowntime"
        @force-check="onDetailForceCheck"
        @add-comment="onDetailAddComment"
        @enable-notifications="onDetailToggleNotifications(true)"
        @disable-notifications="onDetailToggleNotifications(false)"
        @select-host="onSelectHost"
        @bulk-acknowledge="onDetailBulkAcknowledge"
      />
    </div>

    <AckModal
      v-if="detailActions.ackModalObject.value && checkmkUrl"
      :object="detailActions.ackModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="detailActions.closeAckModal"
    />
    <DowntimeModal
      v-if="detailActions.downtimeModalObject.value && checkmkUrl"
      :object="detailActions.downtimeModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="detailActions.closeDowntimeModal"
    />
    <CommentModal
      v-if="detailActions.commentModalObject.value && checkmkUrl"
      :object="detailActions.commentModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="detailActions.commentModalObject.value = null"
    />
    <RemoveDowntimeModal
      v-if="detailActions.removeDowntimeModal.visible && checkmkUrl"
      :downtimes="detailActions.removeDowntimeModal.downtimes"
      :checkmk-url="checkmkUrl"
      :object-name="detailActions.removeDowntimeModal.objectName"
      @close="detailActions.closeRemoveDowntimeModal"
    />
    <BulkAckModal
      v-if="bulkAckModal && checkmkUrl"
      :aggregation-id="bulkAckModal.aggregationId"
      :targets="bulkAckModal.targets"
      :checkmk-url="checkmkUrl"
      @close="closeBulkAckModal"
    />
  </div>
</template>

<style scoped>
.maps-map-view {
  display: flex;
  flex: 1 1 0%;
  flex-direction: column;
  overflow: hidden;
  background: var(--ux-theme-1);

  /* The map's own design values, declared here so everything below inherits
     one set. Only values Checkmk has no token for live here — a map does not
     get its own idea of a radius, a font size or a state colour. */

  /* A near-opaque surface for the controls that float over a map: readable on
     any background, without hiding what is behind them entirely. */
  --maps-map-view-glass: color-mix(in srgb, var(--ux-theme-1) 92%, transparent);

  /* Keeps an icon legible on any backdrop in either theme, where the
     theme-coupled invert it replaces left dark-map icons invisible in the
     light theme and wrongly inverted coloured logos. */
  --maps-map-view-icon-halo: drop-shadow(0 0 1.5px rgb(0 0 0 / 60%))
    drop-shadow(0 0 1.5px rgb(255 255 255 / 90%));

  /* The unfilled remainder of a gauge, and of a utilisation ring. A neutral
     grey rather than a theme surface, because it has to read on a light and a
     dark map background alike. */
  --maps-map-view-gauge-track: rgb(120 120 130 / 50%);

  /* Label plates: light text on a dark plate whatever the theme, since the
     plate sits on the operator's own background image. */
  --maps-map-view-label-bg: rgb(0 0 0 / 65%);
  --maps-map-view-label-ink: var(--white);
  --maps-map-view-hairline: rgb(255 255 255 / 12%);
  --maps-map-view-text-halo: 0 1px 3px rgb(0 0 0 / 90%);

  /* NagVis rendered on white, so an imported map's own text is black. */
  --maps-map-view-classic-ink: rgb(0 0 0);

  /* An object whose image the site does not have. */
  --maps-map-view-missing-ink: var(--color-brown-50);
  --maps-map-view-missing-bg: color-mix(in srgb, var(--color-yellow-50) 25%, transparent);

  /* An object monitoring does not know: a dimmed disc behind its dashed edge. */
  --maps-map-view-missing-fill: rgb(63 63 70 / 40%);
  --maps-map-view-badge-shadow: 0 4px 6px -1px rgb(0 0 0 / 10%), 0 2px 4px -2px rgb(0 0 0 / 10%);
  --maps-map-view-grid: color-mix(in srgb, var(--color-corporate-green-50) 60%, transparent);

  /* Graph series the metric registry has no colour for. Distinct hues from the
     shared palette, so a chart's curves stay tellable apart. */
  --maps-map-view-series-1: var(--color-dark-blue-50);
  --maps-map-view-series-2: var(--color-corporate-green-50);
  --maps-map-view-series-3: var(--color-orange-50);
  --maps-map-view-series-4: var(--color-light-red-50);
  --maps-map-view-series-5: var(--color-purple-50);
  --maps-map-view-series-6: var(--color-cyan-50);
  --maps-map-view-series-7: var(--color-brown-50);
  --maps-map-view-series-8: var(--color-pink-50);

  /* Gadgets keep a dark "instrument" look in either theme: their value text is
     always light, and has to stay legible even sitting directly on a light map
     background — hence the outline below and a neutral track above. */
  --maps-map-view-gadget-bg: rgb(0 0 0 / 55%);
  --maps-map-view-gadget-bar-bg: rgb(0 0 0 / 50%);
  --maps-map-view-gadget-ring: rgb(255 255 255 / 15%);
  --maps-map-view-gadget-ink: rgb(244 244 245);
  --maps-map-view-gadget-ink-dim: rgb(255 255 255 / 80%);
  --maps-map-view-text-outline:
    1px 1px 0 rgb(0 0 0 / 90%), -1px 1px 0 rgb(0 0 0 / 90%), 1px -1px 0 rgb(0 0 0 / 90%),
    -1px -1px 0 rgb(0 0 0 / 90%), 0 0 3px rgb(0 0 0 / 70%);

  /* Checkmk has no semantic token for the two state modifiers. */
  --maps-map-view-acknowledged: var(--color-yellow-50);
  --maps-map-view-downtime: var(--color-light-blue-50);
}

body[data-theme='facelift'] .maps-map-view {
  /* The light theme's own page colour is what a floating control has to sit
     on, and a hairline has to be dark to be seen on it. */
  --maps-map-view-hairline: rgb(0 0 0 / 12%);
}

.maps-map-view__shell {
  position: relative;
  display: flex;
  flex: 1 1 0%;
  overflow: hidden;
}

.maps-map-view__loading {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color-dimmed);
  background: var(--ux-theme-1);
}
</style>
