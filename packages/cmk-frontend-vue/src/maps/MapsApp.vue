<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The Maps app.

It owns the services every surface below it uses, the session it needs before it
can show anything, and which view the page's query string asks for. The page
renders the mount point and the handful of Checkmk URLs the SPA links out to:
everything else shown here the SPA fetches, so there is one data-assembly path
instead of a server-rendered second one.
-->
<script setup lang="ts">
import type { MapsApp } from 'cmk-shared-typing/typescript/maps'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Component, computed, defineAsyncComponent, onUnmounted, watch } from 'vue'

import type { NavState } from '@/maps/services/NavigationService'
import {
  createMapsServices,
  disposeMapsServices,
  provideMapsServices
} from '@/maps/services/context'
import { provideMapsBreadcrumbRoot } from '@/maps/shared/breadcrumb'
import MapsToastContainer from '@/maps/shared/components/MapsToastContainer.vue'
import { provideMapsPageLinks } from '@/maps/shared/pageLinks'

// Lazy, so the heavy views (leaflet, d3) stay in their own chunks and load only
// when one is actually opened.
const homeView = defineAsyncComponent(() => import('@/maps/home/HomeView.vue'))
const mapView = defineAsyncComponent(() => import('@/maps/map/MapView.vue'))
const imagesView = defineAsyncComponent(() => import('@/maps/image-library/ImagesView.vue'))

const props = defineProps<MapsApp>()

const { _t } = usei18n()

// Registered before anything can fail, because the boundary only catches what
// is thrown after ``onErrorCaptured`` ran -- including this component's own boot.
// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const services = createMapsServices()
provideMapsServices(services)
provideMapsPageLinks(props.links)
provideMapsBreadcrumbRoot(props.breadcrumb_root)
onUnmounted(() => {
  disposeMapsServices(services)
})

const { auth, settings, nav } = services

// Scoped to the initially opened map, so the map view's own re-mint is a no-op;
// a lost session bounces to the Checkmk login from inside the service.
void auth.init(nav.state.view === 'map' ? nav.state.name : null)
void settings.load()

const VIEWS: Record<NavState['view'], Component> = {
  home: homeView,
  map: mapView,
  admin: imagesView
}

const currentView = computed(() => VIEWS[nav.state.view])

/** Nothing can be shown before the session is there. */
const ready = computed(() => auth.user.value !== null)

// A boot that will not complete is not a loading state: once the session has
// stayed out, the reason goes through the root error boundary, which is the only
// thing on screen that can carry it -- and offers the reload.
watch(
  () => auth.bootError.value,
  (error) => {
    if (error) {
      throw error
    }
  }
)

// The image library requires the configure permission; bounce home once the
// session says this user has none.
watch(
  () => [nav.state.view, auth.canConfigure.value, auth.user.value] as const,
  () => {
    if (nav.state.view === 'admin' && auth.user.value !== null && !auth.canConfigure.value) {
      nav.replace({ view: 'home' })
    }
  },
  { immediate: true }
)

/** Kiosk and preview show the map alone, without the app's own frame. */
const framed = computed(() => !nav.state.kiosk && !nav.state.preview)
</script>

<template>
  <CmkErrorBoundary>
    <div v-if="!ready" class="maps-app maps-app--booting">
      <CmkLoading />
      {{ _t('Loading…') }}
    </div>
    <div v-else-if="framed" class="maps-app">
      <div class="maps-app__content">
        <component :is="currentView" />
      </div>
    </div>
    <div v-else class="maps-app maps-app--bare">
      <component :is="currentView" />
    </div>
    <MapsToastContainer />
  </CmkErrorBoundary>
</template>

<style scoped>
.maps-app {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-size: var(--font-size-large);
  color: var(--font-color);
  background: var(--ux-theme-1);
}

.maps-app--booting {
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  color: var(--font-color-dimmed);
}

.maps-app__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.maps-app--bare {
  flex-direction: column;
  width: 100vw;
}
</style>

<!--
Host escapes. These selectors live OUTSIDE the app (the mount wrapper and the
custom element), so they cannot be scoped; both are gated on markup only
maps.py emits, so they match nothing on the other pages sharing this bundle.
-->
<style>
/* Mounted inside the Checkmk page, the SPA fills the content area the GUI gave
   it instead of the viewport, so the surrounding chrome stays visible. It also
   becomes the containing block for the app's fixed overlays (action bars, zoom
   pill), which would otherwise anchor to the viewport — and to the corner
   behind the Checkmk sidebar. */
.maps-app--embed {
  height: 100%;
  contain: layout;
}

/* An unstyled custom element is inline and content-sized, which cuts the height
   chain right above the app: the map canvas then resolves to 0px, renders
   nothing and stops hit-testing its nodes. ``CmkApp``'s ``fullPage`` (main.ts)
   carries the height across the wrapper div the element renders inside. */
.maps-app--embed cmk-maps {
  display: block;
}

.maps-app--embed > #app,
.maps-app--embed cmk-maps,
.maps-app--embed .maps-app {
  height: 100%;
}
</style>
