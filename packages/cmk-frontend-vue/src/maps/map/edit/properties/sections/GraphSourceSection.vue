<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Where a graph object takes its curves from: whatever the bound service
measures, a hand-picked set of metrics, or one of Checkmk's own graph
templates.
-->
<script setup lang="ts">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectMetrics } from '@/maps/map/edit/composables/useObjectMetrics'
import { rebindHost } from '@/maps/map/edit/hostBinding'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import { type GraphSource, graphTimeWindows } from '@/maps/map/edit/properties/graphSource'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'

const props = defineProps<{
  metrics: ObjectMetrics
  source: GraphSource
}>()

const form = defineModel<ObjectForm>('form', { required: true })

const emit = defineEmits<{ 'update:source': [source: GraphSource] }>()

const { _t } = usei18n()

// A dropdown rather than a toggle group: the card's control column is ~320px
// and CmkToggleButtonGroup is the form-scale control (150px per option), so
// three options wrap onto two rows. The rows below already read as dropdowns.
const sourceOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'auto', title: _t('auto') },
    { name: 'metrics', title: _t('Metrics') },
    { name: 'template', title: _t('Template') }
  ]
}))

const timeWindowOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: graphTimeWindows().map(({ minutes, title }) => ({
    name: String(minutes),
    title
  }))
}))

const templateOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: null, title: untranslated('—') },
    ...props.metrics.graphTemplates.value.map((template) => ({
      name: template.id,
      title: untranslated(template.title)
    }))
  ]
}))

/**
 * The chips carry titles while the object stores metric ids, so the two are
 * translated at this boundary — an id Checkmk has no title for stands for
 * itself.
 */
const pickedMetricTitles = computed({
  get: () => form.value.graph_metric.map((id) => props.metrics.titleOf(id)),
  set: (titles: string[]) => {
    const idOf = new Map(
      props.metrics.metrics.items.value.map((item) => [item.title as string, item.name as string])
    )
    form.value.graph_metric = titles.map((title) => idOf.get(title) ?? title)
  }
})

function suggestMetrics(query: string): Promise<string[]> {
  const needle = query.trim().toLowerCase()
  const titles = props.metrics.metrics.items.value.map((item) => item.title as string)
  return Promise.resolve(
    needle ? titles.filter((title) => title.toLowerCase().includes(needle)) : titles
  )
}
</script>

<template>
  <PropertySection :title="_t('Metric source')">
    <PropertyRow :label="_t('Host name')">
      <MapsObjectField
        :model-value="form.host_name"
        kind="host"
        :label="_t('Host name')"
        :placeholder="_t('hostname')"
        @update:model-value="rebindHost(form, $event)"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Service')">
      <MapsObjectField
        v-model="form.service_description"
        kind="service"
        :host-name="form.host_name"
        :label="_t('Service')"
        :placeholder="_t('service description')"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Source')">
      <CmkDropdown
        floating
        :model-value="source"
        :options="sourceOptions"
        :label="_t('Source')"
        width="fill"
        @update:model-value="emit('update:source', ($event ?? 'auto') as GraphSource)"
      />
    </PropertyRow>

    <PropertyRow v-if="source === 'metrics'" :label="_t('Metrics')" tall>
      <CmkChipAutocomplete
        v-model="pickedMetricTitles"
        :suggest="suggestMetrics"
        suggest-when-empty
        :placeholder="_t('Add metric…')"
        :aria-label="_t('Metrics')"
      />
    </PropertyRow>

    <PropertyRow
      v-if="source === 'template' && metrics.graphTemplates.value.length > 0"
      :label="_t('Graph template')"
    >
      <CmkDropdown
        floating
        :model-value="form.graph_id"
        :options="templateOptions"
        :label="_t('Graph template')"
        width="fill"
        @update:model-value="form.graph_id = $event || null"
      />
    </PropertyRow>

    <PropertyRow :label="_t('Time window')">
      <CmkDropdown
        floating
        :model-value="String(form.graph_time_window)"
        :options="timeWindowOptions"
        :label="_t('Time window')"
        width="fill"
        @update:model-value="form.graph_time_window = Number($event)"
      />
    </PropertyRow>
  </PropertySection>
</template>
