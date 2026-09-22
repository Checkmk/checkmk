<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { suggestionList, titledSuggestions } from '@/maps/shared/suggestions'
import type { DataElement, MetricChoice } from '@/maps/types/api'

import { isMetriclessBinding } from '../binding'
import { useDataBinding } from '../composables/useDataBinding'

const { _t } = usei18n()

const props = defineProps<{
  element: DataElement
  connectionId: string
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Group/BI bindings have a state but no perf metrics — the picker would only
// mislead ("Bind a host first" on an already-bound element).
const isGroupBinding = computed(() => isMetriclessBinding(props.element))

const binding = useDataBinding(() => props.element.connection_id || props.connectionId)
const metrics = ref<MetricChoice[]>([])
const loadingMetrics = ref(false)
const metricModel = ref('')

const metricList = suggestionList(
  () =>
    titledSuggestions(metrics.value.map((metric) => ({ id: metric.name, title: metric.title }))),
  () => loadingMetrics.value
)

// A metric picked for another object is almost always invalid, so a changed
// binding resets it. Connection and object-type switches null the host/service
// too, so this one watcher covers every binding change.
watch(
  () => [props.element.id, props.element.host_name, props.element.service_description] as const,
  async (curr, prev) => {
    const bindingChanged =
      prev !== undefined && prev[0] === curr[0] && (prev[1] !== curr[1] || prev[2] !== curr[2])

    if (bindingChanged) {
      if (props.element.display.gadget_metric) {
        emit('patch', { display: { ...props.element.display, gadget_metric: null } })
      }
      metricModel.value = ''
    } else {
      metricModel.value = props.element.display.gadget_metric ?? ''
    }

    // Suggestions only matter while the picker is visible — skip the fetch for
    // icon/text-mode elements that merely mount this for the reset above.
    const host = props.element.host_name
    if (!host || props.element.display.mode !== 'gadget') {
      metrics.value = []
      return
    }
    loadingMetrics.value = true
    metrics.value = await binding.metrics(host, props.element.service_description)
    loadingMetrics.value = false
  },
  { immediate: true }
)
</script>

<template>
  <!-- Mounted for every data element (not just gadget mode) so the
       binding-change reset below always runs; the picker itself is only
       relevant once the element actually renders as a gadget. -->
  <template v-if="element.display.mode === 'gadget'">
    <div v-if="!isGroupBinding" class="maps-presentation-gadget-metric-field__field">
      <span class="maps-cap">{{ _t('Metric') }}</span>
      <MapsSuggestionField
        :label="_t('Metric')"
        :model-value="metricModel"
        :list="metricList"
        :placeholder="element.host_name ? _t('Pick a metric…') : _t('Bind a host first')"
        @update:model-value="
          emit('patch', { display: { ...element.display, gadget_metric: $event || null } })
        "
      />
    </div>
    <span v-else class="maps-presentation-gadget-metric-field__note">
      {{
        _t(
          'Groups and BI aggregations carry no metrics — gauge and bar show a state light instead.'
        )
      }}
    </span>
  </template>
</template>

<style scoped>
.maps-presentation-gadget-metric-field__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  min-width: 0;
  flex: 1;
}

.maps-presentation-gadget-metric-field__note {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
