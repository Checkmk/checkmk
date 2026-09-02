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

Only static maps are drawn so far. The other map types, the object slide-in,
the monitoring commands and the editing UI arrive in the commits that follow
this one.
-->
<script setup lang="ts">
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref, useTemplateRef, watch } from 'vue'

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
import StaticMapView from '@/maps/map/static/StaticMapView.vue'
import { useAuth, useConnections, useMaps, useNavigation, useStates } from '@/maps/services/context'
import type { MapElement } from '@/maps/types/api'
import { resolveCheckmkUrl } from '@/maps/utils/deploymentBase'
import { buildCheckmkUrl, openUrl } from '@/maps/utils/mapNavigation'

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

const breadcrumbItems = computed<BreadcrumbItem[]>(() => [
  { title: _t('Maps'), link: nav.href({ view: 'home' }) },
  { title: mapConfig.value?.alias || mapName.value, link: null }
])

/**
 * What a click on an object leads to. The object's own link wins, a map object
 * navigates, Ctrl+Click leaves for Checkmk -- and a plain click opens the
 * object's slide-in, which lands with the commit that adds it.
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
    </div>
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
