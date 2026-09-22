<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The page a map is read on: the chrome around the drawing, the map's own
lifecycle, which map type gets to draw, and the surfaces that open over it --
the object slide-in, the monitoring commands and the editing UI.

The view is reused rather than re-created when the map changes -- a rotation or
a click on a map object swaps the name under the same component -- so the
lifecycle is keyed on the name (``useMapLifecycle``) and not on mount.

This is also where the map's own design values are declared, on the view root,
so every painter below inherits one set of them.

Static, geo, flow and radar maps are drawn so far; the other map types arrive
in the commits that follow this one.
-->
<script setup lang="ts">
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  ref,
  useTemplateRef,
  watch
} from 'vue'

import BulkAckModal from '@/maps/map/commands/BulkAckModal.vue'
import ObjectCommandModals from '@/maps/map/commands/ObjectCommandModals.vue'
import { useObjectActions } from '@/maps/map/commands/useObjectActions'
import MapKioskExit from '@/maps/map/components/MapKioskExit.vue'
import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapProblemsPill, { type ProblemCounts } from '@/maps/map/components/MapProblemsPill.vue'
import MapViewTopbar from '@/maps/map/components/MapViewTopbar.vue'
import { useMapEditor } from '@/maps/map/composables/useMapEditor'
import { useMapFullscreen } from '@/maps/map/composables/useMapFullscreen'
import { useMapLifecycle } from '@/maps/map/composables/useMapLifecycle'
import { provideMapPalette } from '@/maps/map/composables/useMapPalette'
import { useMapRotation } from '@/maps/map/composables/useMapRotation'
import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import { usePreviewBridge } from '@/maps/map/composables/usePreviewBridge'
import DetailDrawer from '@/maps/map/detail/DetailDrawer.vue'
import BundleDialog from '@/maps/map/edit/BundleDialog.vue'
import MapEditTools from '@/maps/map/edit/components/MapEditTools.vue'
import MapObjectActionBar, {
  type MapObjectAction
} from '@/maps/map/edit/components/MapObjectActionBar.vue'
import { useElementRect } from '@/maps/map/edit/composables/useElementRect'
import ObjectPropertiesModal from '@/maps/map/edit/properties/ObjectPropertiesModal.vue'
import MapSettingsModal from '@/maps/map/edit/settings/MapSettingsModal.vue'
import type WorldMapViewType from '@/maps/map/worldmap/WorldMapView.vue'
import type { WorldmapViewport } from '@/maps/map/worldmap/geo'
import {
  useAuth,
  useConnections,
  useMaps,
  useMapsApis,
  useNavigation,
  useSettings,
  useStates,
  useToast
} from '@/maps/services/context'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import { errorText } from '@/maps/shared/errorText'
import type { CommandTarget, MapElement, MapRead, ObjectState } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'
import { resolveCheckmkUrl } from '@/maps/utils/deploymentBase'
import { objectDeleteTitle, objectDisplayName } from '@/maps/utils/dropdownOptions'
import { buildCheckmkUrl, openUrl } from '@/maps/utils/mapNavigation'
import { monitoringObjectId, newMapElement } from '@/maps/utils/model'

// Lazy, one chunk per map type: leaflet rides with the geo map and d3 with the
// flow map, so opening a static map downloads neither. The type imports beside
// them are erased at build, so they pull nothing in.
const flowMapView = defineAsyncComponent(() => import('@/maps/map/flow/FlowMapView.vue'))
const radarMapView = defineAsyncComponent(() => import('@/maps/map/radar/RadarMapView.vue'))
const staticMapView = defineAsyncComponent(() => import('@/maps/map/static/StaticMapView.vue'))
const worldMapView = defineAsyncComponent(() => import('@/maps/map/worldmap/WorldMapView.vue'))

const { _t } = usei18n()
const toast = useToast()
const nav = useNavigation()
const auth = useAuth()
const { objects } = useMapsApis()
const mapsStore = useMaps()
const statesStore = useStates()
const connectionsStore = useConnections()
const settingsStore = useSettings()

const mapName = computed(() => nav.state.name ?? '')
const isKiosk = computed(() => nav.state.kiosk)
const isPreview = computed(() => nav.state.preview)

const { openKioskInNewTab, exitFullscreen } = useMapFullscreen(mapName, isKiosk)

const mapConfig = computed(() => mapsStore.currentMap.value)
// Whether the current user may edit *this* map: the per-map pagetype
// capability the backend stamps on the map-list entry (built-ins and
// unauthorized foreign maps are read-only — admin rights ride in via the
// "edit foreign maps" permission, not via configure/admin status).
const mapListEntry = computed(() => mapsStore.maps.value.find((b) => b.name === mapName.value))
const canEdit = computed(() => mapListEntry.value?.can_edit === true)
/**
 * The open map as the settings form wants it: the daemon config, plus the
 * envelope only the map-list entry carries — ownership, sharing and the right
 * to delete.
 *
 * Both halves are required. The form saves ``public`` on every save, so an
 * envelope guessed from a missing list entry would read as private and
 * unpublish a shared map on an unrelated edit — hence ``null`` until the list
 * is there, which is also when there is nothing to authorize editing against.
 */
const mapConfigAsRead = computed<MapRead | null>(() => {
  const cfg = mapConfig.value
  const listed = mapListEntry.value
  if (!cfg || !listed) {
    return null
  }
  const { objects, ...rest } = cfg
  return {
    ...listed,
    ...rest,
    icon_size: cfg.icon_size ?? null,
    view_type: cfg.view.type,
    object_count: objects.length
  }
})
// Every map type not drawn yet says so; until its own commit lands, that beats
// rendering it as something it is not.
const isStatic = computed(() => (mapConfig.value?.view.type ?? 'static') === 'static')
const isWorldmap = computed(() => mapConfig.value?.view.type === 'worldmap')
const isFlowmap = computed(() => mapConfig.value?.view.type === 'flow')
const isRadar = computed(() => mapConfig.value?.view.type === 'radar')

// The map's search, wherever the map type offers one.
const mapFilterNeedle = ref('')
watch(mapName, () => {
  mapFilterNeedle.value = ''
})
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

const worldmapViewRef = useTemplateRef<InstanceType<typeof WorldMapViewType>>('worldMapViewRef')

// Which element the action bar hangs off. The selection is an id -- it is made
// by click, by marquee, by keyboard and by placing a new object -- so the node
// is looked up inside this view, the way the canvas' own gestures do
// (``useCanvasLineAnchors``), rather than reached for across the document.
const selectedObjectEl = ref<HTMLElement | null>(null)
// Bumped on every geo-map pan/zoom so the action bar re-anchors to the marker:
// panning moves the whole marker pane, which no marker's own element sees.
const geoViewTick = ref(0)
const selectedRect = useElementRect(selectedObjectEl, () => geoViewTick.value)

watch(
  [() => editor.selectedObjectId.value, () => geoViewTick.value],
  async ([id]) => {
    await nextTick()
    selectedObjectEl.value = id
      ? (root.value?.querySelector<HTMLElement>(`[data-object-id="${CSS.escape(id)}"]`) ?? null)
      : null
  },
  { immediate: true }
)

// Above the object where there is room for it, below it otherwise -- the
// toolbar must not cover what is being edited.
const actionBarStyle = computed(() => {
  const { top, left, width, bottom } = selectedRect
  if (!selectedObjectEl.value || width === 0) {
    return null
  }
  const barHeightApprox = 36
  const gap = 8
  const aboveTop = top - barHeightApprox - gap
  const useAbove = aboveTop >= 8
  return {
    top: `${useAbove ? aboveTop : bottom + gap}px`,
    left: `${left + width / 2}px`,
    transform: 'translateX(-50%)'
  }
})

// The editing controls are for whoever may change *this* map, and only while
// the view is not doing something else: a kiosk screen, a live preview, or
// triage in the detail drawer. Flow and radar maps derive their content, so
// there is nothing on them to arrange.
const showsEditTools = computed(
  () =>
    canEdit.value &&
    !isKiosk.value &&
    !isPreview.value &&
    !!mapConfig.value &&
    !mapConfig.value.readonly &&
    (isStatic.value || isWorldmap.value) &&
    !drawerObject.value
)

// The toolbar belongs to a settled selection: not behind the properties card
// it opens, and not while another object is being placed.
const showsActionBar = computed(
  () =>
    editor.editMode.value &&
    !!editor.selectedObjectId.value &&
    !propsModalObject.value &&
    !editor.draft.type
)

// The edit tools keep their place under an open dialog, but not the keyboard:
// every one of these covers the map with a backdrop, so a key pressed in one
// belongs to it and not to the object behind it.
const editKeyboardActive = computed(
  () =>
    !propsModalObject.value &&
    !showSettings.value &&
    !deleteTargetObject.value &&
    !bulkDeleteOpen.value &&
    !bundleDialogOpen.value &&
    !bulkAckModal.value
)

const selectedObjectAnchor = computed<AnchorRect | null>(() => {
  if (!selectedObjectEl.value || selectedRect.width === 0) {
    return null
  }
  return {
    left: selectedRect.left,
    top: selectedRect.top,
    right: selectedRect.right,
    bottom: selectedRect.bottom
  }
})

const propsModalObject = ref<MapElement | null>(null)

/**
 * The box the properties card sits beside, or ``null`` when it was reached
 * from somewhere with nothing to sit next to and opens as a centered dialog.
 *
 * It stays live rather than being snapshotted at open time:
 * ``selectedObjectAnchor`` follows the object as the canvas re-lays out under
 * the open card (a window resize moves every object), and a stale box would
 * place the card beside where the object used to be. The box the card was
 * opened on carries a frame in which the object is momentarily unmeasurable,
 * so the card never flips to a centered dialog under the operator.
 */
const openedOnAnchor = ref<AnchorRect | null>(null)
const propsModalAnchor = computed<AnchorRect | null>(() =>
  openedOnAnchor.value ? (selectedObjectAnchor.value ?? openedOnAnchor.value) : null
)
const deleteTargetObject = ref<MapElement | null>(null)
const bulkDeleteOpen = ref(false)

/** One place for what the selected object's toolbar can trigger. */
function onObjectAction(action: MapObjectAction): void {
  const object = selectedObject.value
  if (!object) {
    return
  }
  switch (action) {
    case 'edit':
      openPropsModal(object, selectedObjectAnchor.value)
      break
    case 'duplicate':
      void editor.duplicateSelected()
      break
    case 'detach':
      onObjectDetach(object)
      break
    case 'front':
      void editor.moveSelectedLayer('front')
      break
    case 'back':
      void editor.moveSelectedLayer('back')
      break
    case 'bundle':
      bundleDialogOpen.value = true
      break
    case 'unbundle':
      void editor.unbundleSelected()
      break
    case 'delete':
      deleteSelection()
      break
  }
}

/** Deleting several objects at once is confirmed as a group, not one by one. */
function deleteSelection() {
  if (editor.selectedCount.value > 1) {
    bulkDeleteOpen.value = true
  } else {
    deleteTargetObject.value = selectedObject.value
  }
}

async function confirmBulkDelete() {
  bulkDeleteOpen.value = false
  await editor.deleteAllSelected()
}

const deleteDialogTitle = computed(() => {
  const obj = deleteTargetObject.value
  return obj ? objectDeleteTitle(obj, _t) : _t('Delete object')
})

function openPropsModal(obj: MapElement, anchor?: AnchorRect | null) {
  editor.selectObject(obj.id)
  openedOnAnchor.value = anchor ?? null
  propsModalObject.value = obj
}

/**
 * The object a click on the canvas just created, until its properties are saved.
 *
 * Placing writes the object straight away -- the map has to show it somewhere to
 * let the operator judge the spot. The properties modal that opens on top of it
 * is therefore an *undo* point, not a create form: dismissing it has to take the
 * object back out, or "Cancel" would leave behind exactly what it says it did
 * not do, and the only way back would be to find the thing and delete it.
 */
const justPlacedId = ref<string | null>(null)

function onObjectPlaced() {
  const obj = selectedObject.value
  if (!obj) {
    return
  }
  justPlacedId.value = obj.id
  openPropsModal(obj)
}

// The viewport the geo map opens on is part of the map's settings, so picking
// it here opens the settings slide-in with the picked viewport in hand.
function onSaveWorldmapViewport(at: WorldmapViewport) {
  settingsWorldmapView.value = { ...at }
  settingsParentMapSize.value = worldmapViewRef.value?.getContainerSize() ?? null
  showSettings.value = true
}

function _closePropsModal() {
  propsModalObject.value = null
  openedOnAnchor.value = null
  justPlacedId.value = null
}

/** Dismissing the modal: an object that only exists because of it goes with it. */
async function onPropsModalClose() {
  const placed = justPlacedId.value === null ? null : propsModalObject.value
  _closePropsModal()
  if (placed) {
    await deleteObject(placed)
  }
}

async function onPropsModalSave(updates: Record<string, unknown>) {
  if (!propsModalObject.value) {
    _closePropsModal()
    return
  }
  try {
    justPlacedId.value = null
    await editor.updateObjectProperties(propsModalObject.value.id, updates)
  } catch (e) {
    toast.error(errorText(e, _t('Save failed')))
  } finally {
    // Always close the modal so its local "saving" state resets even if
    // the backend rejected the update — otherwise the Save button stays
    // stuck on "Saving…" with no feedback.
    _closePropsModal()
  }
}

/** Deleting goes through the selection, whichever surface asked for it. */
async function deleteObject(obj: MapElement) {
  editor.selectObject(obj.id)
  await editor.deleteAllSelected()
}

/** A line bound to an object follows it; detaching frees its endpoints. */
function onObjectDetach(obj: MapElement) {
  void editor.updateObjectProperties(obj.id, { start_ref: null, end_ref: null })
}

async function onPropsModalDelete() {
  const obj = propsModalObject.value
  _closePropsModal()
  if (obj) {
    await deleteObject(obj)
  }
}

function onPropsModalDetach() {
  const obj = propsModalObject.value
  _closePropsModal()
  if (obj) {
    onObjectDetach(obj)
  }
}

function onToggleEditMode() {
  editor.toggleEditMode()
}

function onObjectDelete(obj: MapElement) {
  deleteTargetObject.value = obj
}

async function confirmObjectDelete() {
  const obj = deleteTargetObject.value
  deleteTargetObject.value = null
  if (obj) {
    await deleteObject(obj)
  }
}

const selectedObject = computed<MapElement | null>(() => {
  if (!editor.selectedObjectId.value || !mapConfig.value) {
    return null
  }
  return mapConfig.value.objects.find((o) => o.id === editor.selectedObjectId.value) ?? null
})

const selectedHostCount = computed(() => {
  const ids = new Set(editor.selectedIds.value)
  return (mapConfig.value?.objects ?? []).filter(
    (o) =>
      ids.has(o.id) &&
      o.type === 'host' &&
      o.host_name &&
      o.lat !== null &&
      o.lat !== undefined &&
      o.lng !== null &&
      o.lng !== undefined
  ).length
})
const canBundle = computed(() => isWorldmap.value && selectedHostCount.value >= 2)
const selectedIsBundle = computed(
  () => editor.selectedCount.value <= 1 && !!selectedObject.value?.bundle_kind
)

const bundleDialogOpen = ref(false)
function onBundleConfirm(payload: { name: string; kind: 'static' | 'location' }) {
  bundleDialogOpen.value = false
  void editor.bundleSelected(payload.name, payload.kind)
}

// ---- Detail drawer (shared across the static and geo maps) ----

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
const drawerCommands = detailActions.drawerHandlers(() => detailDrawerObject.value)

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
  // still open in the same slidein — the parent state cycle lifts onto the
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
  const transientId = `transient:${monitoringObjectId(hostName, serviceDescription ?? null)}`
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

function closeDetail() {
  detailDrawerObject.value = null
  drawerSeedState.value = null
}

/**
 * Bulk-acknowledge contributing leaves of a BI aggregation. Opens the
 * BulkAckModal — that previews the targets, lets the operator review/edit
 * the comment (pre-filled with "Bulk-ack: <aggregation_id>" so audit logs
 * trace back to the originating aggregation), and runs the per-leaf ack
 * loop with progress feedback: N acks have no atomic undo, so a misclick must
 * not fire them.
 */
function onDetailBulkAcknowledge(targets: CommandTarget[]) {
  if (!targets.length) {
    return
  }
  const obj = detailDrawerObject.value
  const aggregationId = obj?.aggregation_id ?? obj?.id ?? 'unknown'
  bulkAckModal.value = { aggregationId, targets }
}

const bulkAckModal = ref<{
  aggregationId: string
  targets: CommandTarget[]
} | null>(null)

/**
 * What a click on an object leads to. In edit mode it selects; otherwise the
 * object's own link wins, a map object navigates, Ctrl+Click leaves for
 * Checkmk -- and a plain click opens the object's slide-in.
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

/**
 * A host dropped onto a geo map goes where the host is, if monitoring knows:
 * asking the operator to find a site on the globe by hand would be absurd.
 */
async function onStartPlacing() {
  const draft = editor.draft
  if (isWorldmap.value && mapConfig.value?.connection_id && draft.host_name) {
    try {
      const geo = await objects.fetchHostGeo(draft.host_name)
      if (geo) {
        editor.startPlacing()
        await editor.placeAtLatLng(geo.lat, geo.lng)
        onObjectPlaced()
        return
      }
    } catch {
      // Geo lookup failed (host unknown to the site or connection down); fall
      // through to plain placing so the operator can still drop the object.
    }
  }
  editor.startPlacing()
}

const FLOW_PROBLEMS_DEFAULT: ProblemCounts = {
  critical: 0,
  warning: 0,
  hostsWithProblems: 0,
  total: 0
}
const flowProblems = ref<ProblemCounts>({ ...FLOW_PROBLEMS_DEFAULT })
const flowDrawerObject = ref<MapElement | null>(null)
// Only the flow map itself reports its slide-in closing, so if it goes away
// with one open — a rotation to another map type — nothing would ever clear
// this, and the dimmed topbar and its breadcrumb would outlive the node.
watch(isFlowmap, (flow) => {
  if (!flow) {
    flowDrawerObject.value = null
  }
})
const drawerObject = computed<MapElement | null>(
  () => detailDrawerObject.value ?? flowDrawerObject.value
)
// The map itself stays the breadcrumb's last level until a slide-in is open:
// then the map name links back to the bare map.
const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
  const mapTitle = mapConfig.value?.alias || mapName.value
  const items: BreadcrumbItem[] = [{ title: _t('Maps'), link: nav.href({ view: 'home' }) }]
  if (drawerObject.value) {
    items.push({ title: mapTitle, link: nav.href({ view: 'map', name: mapName.value }) })
    items.push({ title: objectDisplayName(drawerObject.value, _t), link: null })
  } else {
    items.push({ title: mapTitle, link: null })
  }
  return items
})

// The map types that show it read this from the same place, so a flow map and
// a folder tree are not passed it.
const { problemsOnly } = useMapViewState()

watch(mapName, () => {
  flowProblems.value = { ...FLOW_PROBLEMS_DEFAULT }
})
const showSettings = ref(false)
const settingsWorldmapView = ref<WorldmapViewport | null>(null)
const settingsParentMapSize = ref<{ width: number; height: number } | null>(null)

// The picker runs on the map itself: the geo map's view shows the banner and
// answers with the viewport the operator arrived at.
async function onSettingsPickWorldmapView(done: (at: WorldmapViewport | null) => void) {
  done((await worldmapViewRef.value?.pickViewport()) ?? null)
}

function onSettingsWorldmapViewChange(at: WorldmapViewport) {
  worldmapViewRef.value?.setViewport(at)
}

function openSettings() {
  if (!mapConfig.value) {
    return
  }
  settingsWorldmapView.value = null
  settingsParentMapSize.value = isWorldmap.value
    ? (worldmapViewRef.value?.getContainerSize() ?? null)
    : null
  showSettings.value = true
}

async function onSettingsUpdated() {
  // Settings save may have changed the connection or filter; refresh
  // monitoring states so the canvas reflects the new scope. Flipping
  // ``initialLoad`` gives radar / flow maps a spinner in the gap.
  stopRotation()
  scheduleRotation(mapsStore.currentMap.value?.rotation_interval ?? 0)
  await statesStore.refreshWithIndicator()
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

// A bulk ack's effect shows up in monitoring a moment later, so closing it
// asks the state stream for a fresh picture -- the same thing the
// single-object modals do via ``useObjectActions``. A dialog the operator
// dismissed without sending anything has nothing to show.
function closeBulkAckModal(sent: boolean): void {
  bulkAckModal.value = null
  if (sent) {
    statesStore.refreshAfterCommand()
  }
}
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
      :can-configure="canEdit && !mapConfig?.readonly"
      :dimmed="!!drawerObject"
      @toggle-rotation="toggleRotationPause"
      @open-full-screen="openKioskInNewTab"
      @open-settings="openSettings"
    >
      <template #breadcrumb>
        <CmkBreadcrumb :items="breadcrumbItems" />
      </template>
      <template #status>
        <MapProblemsPill v-if="isFlowmap && flowProblems.total > 0" :problems="flowProblems" />
      </template>
    </MapViewTopbar>

    <MapKioskExit v-if="isKiosk" @exit="exitFullscreen" />

    <!-- Map area + optional edit panel. The detail drawer opens over it, so it
         stays under the topbar. -->
    <div class="maps-map-view__shell">
      <div v-if="isLoading" class="maps-map-view__loading">
        <CmkLoading />
        <span>{{ _t('Loading map…') }}</span>
      </div>
      <world-map-view
        v-if="isWorldmap"
        ref="worldMapViewRef"
        v-model:filter-needle="mapFilterNeedle"
        v-model:problems-only="problemsOnly"
        :config="mapConfig"
        :states="statesStore.states.value"
        :editor="editor"
        :error="mapsStore.error.value"
        :preview="isPreview"
        :checkmk-url="checkmkUrl"
        @object-click="onObjectClick"
        @object-properties="openPropsModal"
        @object-delete="onObjectDelete"
        @placed="onObjectPlaced"
        @view-changed="geoViewTick++"
        @save-viewport="onSaveWorldmapViewport"
      />

      <radar-map-view
        v-else-if="isRadar"
        v-model:filter-needle="mapFilterNeedle"
        v-model:problems-only="problemsOnly"
        :config="mapConfig"
        :error="mapsStore.error.value"
        :preview="isPreview"
        @object-click="onObjectClick"
      />

      <flow-map-view
        v-else-if="isFlowmap"
        v-model:filter-needle="mapFilterNeedle"
        :config="mapConfig"
        :error="mapsStore.error.value"
        :kiosk="isKiosk"
        :preview="isPreview"
        :checkmk-url="checkmkUrl"
        @update:problems="flowProblems = $event"
        @drawer-object="flowDrawerObject = $event"
      />

      <MapPlaceholder
        v-else-if="!isStatic"
        :message="_t('This map type cannot be shown yet')"
        variant="empty"
      />

      <static-map-view
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
        @object-properties="openPropsModal"
        @object-delete="onObjectDelete"
        @placed="onObjectPlaced"
      />

      <!-- Shared detail drawer for static / worldmap / radar maps -->
      <DetailDrawer
        v-if="!isFlowmap"
        :object="detailDrawerObject"
        :state="detailDrawerState"
        :checkmk-url="checkmkUrl"
        :connection-id="detailDrawerObject?.connection_id ?? mapConfig?.connection_id ?? null"
        :selectable-hosts="selectableHostNames"
        :unattended="isKiosk || isPreview"
        v-on="drawerCommands"
        @close="closeDetail"
        @select-host="onSelectHost"
        @bulk-acknowledge="onDetailBulkAcknowledge"
      />
    </div>

    <ObjectCommandModals :actions="detailActions" :checkmk-url="checkmkUrl" />

    <BulkAckModal
      v-if="bulkAckModal"
      :origin="bulkAckModal.aggregationId"
      :targets="bulkAckModal.targets"
      @close="closeBulkAckModal"
    />

    <!-- The editing controls and the selected object's toolbar, over the map.
         Both step aside while the detail drawer is open: that is triage, not
         editing. -->
    <Teleport to="#app">
      <MapEditTools
        v-if="showsEditTools"
        :editor="editor"
        :connection-id="mapConfig?.connection_id ?? ''"
        :keyboard-active="editKeyboardActive"
        :offers-add-object="true"
        :offers-grid="!isWorldmap"
        @start-placing="onStartPlacing()"
        @toggle-edit-mode="onToggleEditMode"
        @delete-selection="onObjectAction('delete')"
        @duplicate-selection="onObjectAction('duplicate')"
      />
    </Teleport>

    <Teleport to="#app">
      <Transition
        enter-from-class="maps-map-view__bar-enter-from"
        enter-active-class="maps-map-view__bar-enter-active"
        leave-to-class="maps-map-view__bar-leave-to"
        leave-active-class="maps-map-view__bar-leave-active"
      >
        <MapObjectActionBar
          v-if="showsActionBar && selectedObject && actionBarStyle"
          :style="actionBarStyle"
          :object="selectedObject"
          :selected-count="editor.selectedCount.value"
          :can-bundle="canBundle"
          :is-bundle="selectedIsBundle"
          @act="onObjectAction"
        />
      </Transition>
    </Teleport>

    <MapsConfirmDialog
      :open="!!deleteTargetObject"
      variant="error"
      :title="deleteDialogTitle"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="confirmObjectDelete"
      @cancel="deleteTargetObject = null"
    />

    <MapsConfirmDialog
      :open="bulkDeleteOpen"
      variant="error"
      :title="_t('Delete %{n} objects?', { n: editor.selectedCount.value })"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="confirmBulkDelete"
      @cancel="bulkDeleteOpen = false"
    />

    <BundleDialog
      v-if="bundleDialogOpen"
      :host-count="selectedHostCount"
      @confirm="onBundleConfirm"
      @close="bundleDialogOpen = false"
    />

    <Teleport to="#app">
      <ObjectPropertiesModal
        v-if="propsModalObject"
        :object="propsModalObject"
        :state="statesStore.states.value[propsModalObject.id]"
        :connection-id="mapConfig?.connection_id ?? ''"
        :map-type="mapConfig?.view.type"
        :map-icon-size="mapConfig?.icon_size ?? settingsStore.settings.value.icon_size"
        :map-default-z="mapConfig?.default_z ?? 1"
        :checkmk-url="checkmkUrl"
        :anchor-rect="propsModalAnchor"
        @close="onPropsModalClose"
        @save="onPropsModalSave"
        @delete="onPropsModalDelete"
        @detach="onPropsModalDetach"
      />
    </Teleport>

    <MapSettingsModal
      v-if="showSettings && mapConfigAsRead"
      :map="mapConfigAsRead"
      :worldmap-view="settingsWorldmapView"
      :parent-map-size="settingsParentMapSize"
      @close="showSettings = false"
      @updated="onSettingsUpdated"
      @pick-worldmap-view="onSettingsPickWorldmapView"
      @worldmap-view-change="onSettingsWorldmapViewChange"
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

.maps-map-view__bar-enter-from,
.maps-map-view__bar-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.maps-map-view__bar-enter-active {
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
}

.maps-map-view__bar-leave-active {
  transition: all 0.1s cubic-bezier(0.4, 0, 1, 1);
}
</style>
