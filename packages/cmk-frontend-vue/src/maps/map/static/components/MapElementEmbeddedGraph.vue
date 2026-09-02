<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A graph object that shows something the operator pointed it at by URL, rather
than metrics Maps fetched itself — a Grafana panel, a rendered PNG from another
system.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onUnmounted, ref, watch, watchEffect } from 'vue'

import type { MapElement } from '@/maps/types/api'

import MapElementGraphNotice from './MapElementGraphNotice.vue'

const { _t } = usei18n()

const props = defineProps<{ object: MapElement }>()

const loadFailed = ref(false)
watch(
  () => props.object.graph_url,
  () => {
    loadFailed.value = false
  }
)

/**
 * Render-sink guard. A map saved before the server-side scheme allowlist may
 * still carry a hostile URL, so only ever embed http(s) — a relative URL
 * resolves against the page origin and passes.
 */
const embeddable = computed(() => {
  const url = props.object.graph_url
  if (!url) {
    return ''
  }
  try {
    const { protocol } = new URL(url, window.location.href)
    return protocol === 'http:' || protocol === 'https:' ? url : ''
  } catch {
    return ''
  }
})

// A cache-busting counter, bumped on the object's own refresh interval: the
// embedded resource is somebody else's, so there is nothing to re-fetch but the
// URL itself.
const refreshTick = ref(0)
let refreshTimer: ReturnType<typeof setInterval> | null = null

function stopRefreshing(): void {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

watchEffect(() => {
  stopRefreshing()
  const interval = props.object.graph_refresh_interval ?? 0
  if (interval > 0) {
    refreshTimer = setInterval(() => {
      refreshTick.value++
    }, interval * 1000)
  }
})
onUnmounted(stopRefreshing)

const source = computed(() => {
  const url = embeddable.value
  if (!url || (props.object.graph_refresh_interval ?? 0) === 0) {
    return url
  }
  return `${url}${url.includes('?') ? '&' : '?'}_t=${refreshTick.value}`
})
</script>

<template>
  <MapElementGraphNotice
    v-if="!embeddable || loadFailed"
    dashed
    :message="object.graph_url ? _t('Load failed') : _t('No URL configured')"
  />
  <img
    v-else-if="object.graph_embed_type !== 'iframe'"
    :src="source"
    class="maps-map-element-embedded-graph__image"
    draggable="false"
    @error="loadFailed = true"
    @load="loadFailed = false"
  />
  <!-- No allow-same-origin: together with allow-scripts it would void the
       sandbox for same-origin content. An embedded graph needs to render and
       run its own scripts, never to reach our origin — cookies, the session
       token in sessionStorage, the parent DOM. -->
  <iframe
    v-else
    :src="embeddable"
    class="maps-map-element-embedded-graph__frame"
    sandbox="allow-scripts"
  />
</template>

<style scoped>
.maps-map-element-embedded-graph__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  border-radius: 8px;
}

.maps-map-element-embedded-graph__frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 8px;
}
</style>
