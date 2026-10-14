<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map object shown as an instrument — a gauge, a bar, a traffic light.

The reading behind a gadget without a configured metric is Checkmk's own
Perf-O-Meter, not the raw perfdata: the Perf-O-Meter knows the plug-in's focus
range, so a gauge can fill even for a metric that reports no maximum, and it
supplies the value label already formatted the way Checkmk formats it.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import GadgetRenderer from '@/maps/map/components/GadgetRenderer.vue'
import { useMetricUnits } from '@/maps/map/composables/useMetricUnits'
import { usePerfometer } from '@/maps/map/composables/usePerfometer'
import type { MapElement, ObjectState } from '@/maps/types/api'
import { objectCaption } from '@/maps/utils/dropdownOptions'

import MapElementLabel from './MapElementLabel.vue'

const { _t } = usei18n()

/**
 * Object kinds with a state but no metrics of their own. A gauge or a bar would
 * read "—" forever, so they show the state light instead.
 */
const STATE_ONLY_TYPES = new Set(['hostgroup', 'servicegroup', 'dyngroup', 'aggregation'])

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  connectionId?: string | undefined
  /** The NagVis-compatible renderer. */
  classic?: boolean
}>()

const configuredType = computed(() => props.object.display?.gadget_type || 'gauge')
const gadgetType = computed(() =>
  STATE_ONLY_TYPES.has(props.object.type) ? 'trafficlight' : configuredType.value
)

const binding = {
  connectionId: () => props.connectionId,
  hostName: () => props.object.host_name,
  serviceDescription: () => props.object.service_description,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command
}

// Both come from one lookup. The raw-value gadget needs the Perf-O-Meter too:
// it is the reading of any gadget without a configured metric.
const readsMetrics = () => gadgetType.value !== 'trafficlight'
const perfometer = usePerfometer({ ...binding, enabled: readsMetrics })
const metricUnits = useMetricUnits({ ...binding, enabled: readsMetrics })
</script>

<template>
  <div class="maps-map-element-gadget">
    <div :class="selected ? 'maps-map-element-gadget__frame--selected' : ''">
      <GadgetRenderer
        :type="gadgetType"
        :metric="object.display?.gadget_metric ?? null"
        :state="state"
        :size="iconSize"
        :perfometer="perfometer"
        :metric-units="metricUnits"
      />
    </div>
    <MapElementLabel
      v-if="object.label?.show && state?.state !== 'NO_PERMISSION'"
      :object="object"
      :text="objectCaption(object, state, _t)"
      placement="stacked"
      :classic="classic"
    />
  </div>
</template>

<style scoped>
.maps-map-element-gadget {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.maps-map-element-gadget__frame--selected {
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 2px var(--ux-theme-1),
    0 0 0 4px var(--interactive-accent);
}
</style>
