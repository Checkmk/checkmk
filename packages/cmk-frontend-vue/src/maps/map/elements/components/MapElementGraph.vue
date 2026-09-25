<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A graph object, in its configured footprint.

There are two kinds: one bound to a host or service, whose metrics Maps fetches
and draws itself, and one pointed at a URL somebody else renders. Both keep the
same frame, caption and resize grip, so which kind an object is stays a detail
of what fills the box.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { useMapElementChart } from '@/maps/map/elements/composables/useMapElementChart'
import type { MapElement, ObjectState } from '@/maps/types/api'

import MapElementChart from './MapElementChart.vue'
import MapElementEmbeddedGraph from './MapElementEmbeddedGraph.vue'
import MapElementGraphNotice from './MapElementGraphNotice.vue'
import MapElementLabel from './MapElementLabel.vue'
import MapElementResizeHandle from './MapElementResizeHandle.vue'

/** Footprint of a graph object that was never resized. */
const DEFAULT_WIDTH = 400
const DEFAULT_HEIGHT = 200

const { _t } = usei18n()

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  selected?: boolean
  editMode?: boolean
  /** Live size while the operator is dragging the resize grip. */
  resizeOverride?: { width: number; height: number } | undefined
  connectionId?: string | undefined
  /** The NagVis-compatible renderer. */
  classic?: boolean
}>()

defineEmits<{ 'resize-start': [event: PointerEvent] }>()

const forbidden = computed(() => props.state?.state === 'NO_PERMISSION')
const native = computed(() => !!props.object.host_name)

const chart = useMapElementChart({
  object: () => props.object,
  state: () => props.state,
  connectionId: () => props.connectionId,
  enabled: () => native.value && !forbidden.value
})

const frameStyle = computed(() => ({
  width: `${props.resizeOverride?.width ?? props.object.graph_width ?? DEFAULT_WIDTH}px`,
  height: `${props.resizeOverride?.height ?? props.object.graph_height ?? DEFAULT_HEIGHT}px`
}))

const waitingMessage = computed(() =>
  chart.timedOut.value
    ? _t('No data for "%{service}" on %{host}', {
        service: props.object.service_description || props.object.host_name || '',
        host: props.object.host_name ?? ''
      })
    : _t('Waiting for data…')
)
</script>

<template>
  <div class="maps-map-element-graph" :style="frameStyle">
    <div v-if="forbidden" class="maps-map-element-graph__forbidden" />

    <template v-else-if="native">
      <MapElementGraphNotice
        v-if="!chart.hasData.value"
        :message="waitingMessage"
        :dashed="editMode"
      />
      <MapElementChart
        v-else
        :chart="chart"
        :state="state"
        :pinned-metric="object.graph_metric?.[0]"
      />
    </template>

    <MapElementEmbeddedGraph v-else :object="object" />

    <MapElementLabel
      v-if="object.label?.show && object.label?.text && !forbidden"
      :object="object"
      :text="object.label.text"
      placement="caption"
      :classic="classic"
    />

    <MapElementResizeHandle v-if="editMode" @start="$emit('resize-start', $event)" />

    <div v-if="selected" class="maps-map-element-graph__selection" />
  </div>
</template>

<style scoped>
.maps-map-element-graph {
  position: relative;
  user-select: none;
}

.maps-map-element-graph__forbidden {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  background: color-mix(in srgb, var(--ux-theme-1) 20%, transparent);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-4);
}

.maps-map-element-graph__selection {
  position: absolute;
  inset: 0;
  border-radius: var(--dimension-4);
  box-shadow:
    0 0 0 1px var(--ux-theme-1),
    0 0 0 3px var(--color-corporate-green-50);
  pointer-events: none;
}
</style>
