<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A line: what it reads its throughput from, how it is drawn, and — on a canvas
map — where its two ends sit.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectMetrics } from '@/maps/map/edit/composables/useObjectMetrics'
import type { ObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import type { LinePerfdataLabel, MapElement, MapViewType } from '@/maps/types/api'
import { linePerfdataLabelOptions, lineStyleOptions } from '@/maps/utils/dropdownOptions'

const props = defineProps<{
  object: MapElement
  suggestions: ObjectSuggestions
  metrics: ObjectMetrics
  mapType: MapViewType | undefined
}>()

const form = defineModel<ObjectForm>('form', { required: true })

defineEmits<{ detach: [] }>()

const { _t } = usei18n()

const styleOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: lineStyleOptions(_t)
}))
const perfdataLabelOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: linePerfdataLabelOptions(_t)
}))

const isAttached = computed(() => !!(props.object.start_ref || props.object.end_ref))
/** Both the labels and the weather colouring read the line's metric. */
const readsPerfdata = computed(
  () => form.value.line_perfdata_label !== 'none' || form.value.line_weather_color
)
const hasOwnCoordinates = computed(() => props.mapType !== 'worldmap')
</script>

<template>
  <PropertySection :title="_t('Monitoring object')">
    <PropertyRow :label="_t('Hostname')">
      <MapsSuggestionField
        v-model="form.host_name"
        :label="_t('Hostname')"
        :list="suggestions.hosts"
        :placeholder="_t('hostname')"
        :empty-hint="_t('No hosts available')"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Service')">
      <MapsSuggestionField
        v-model="form.service_description"
        :label="_t('Service')"
        :list="suggestions.services"
        :placeholder="_t('service description (optional)')"
        :empty-hint="form.host_name ? _t('No services for this host') : undefined"
      />
    </PropertyRow>
  </PropertySection>

  <PropertySection v-if="isAttached" :title="_t('Connection')">
    <p class="maps-line-section__note">
      {{ _t('This line is attached to an object and follows it.') }}
    </p>
    <CmkButton variant="secondary" @click="$emit('detach')">
      {{ _t('Detach from object') }}
    </CmkButton>
  </PropertySection>

  <PropertySection :title="_t('Line')">
    <PropertyRow :label="_t('Z')">
      <CmkInput v-model="form.z" type="number" min="0" max="999" />
    </PropertyRow>
    <PropertyRow :label="_t('Style')">
      <CmkDropdown
        floating
        :model-value="form.line_style"
        :options="styleOptions"
        :label="_t('Style')"
        width="fill"
        @update:model-value="form.line_style = $event || null"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Perfdata label')">
      <CmkDropdown
        floating
        :model-value="form.line_perfdata_label"
        :options="perfdataLabelOptions"
        :label="_t('Perfdata label')"
        width="fill"
        @update:model-value="form.line_perfdata_label = ($event as LinePerfdataLabel) || 'none'"
      />
    </PropertyRow>
    <CmkCheckbox
      v-model="form.line_weather_color"
      :label="_t('Color by utilization (weathermap)')"
    />

    <!-- The inbound metric is drawn left of the midpoint. -->
    <PropertyRow v-if="readsPerfdata" :label="_t('Metric (in)')">
      <MapsSuggestionField
        v-model="form.weathermap_metric"
        :label="_t('Metric (in)')"
        :list="metrics.metrics"
        :placeholder="_t('first metric')"
        :empty-hint="_t('No metrics available')"
      />
    </PropertyRow>
    <!--
      The outbound metric drives the second gradient colour and the label right
      of the midpoint. Offered only once an inbound one is set: on its own it
      would colour the inbound half from an arbitrary first perfdata metric.
    -->
    <PropertyRow v-if="readsPerfdata && !!form.weathermap_metric" :label="_t('Metric (out)')">
      <MapsSuggestionField
        v-model="form.weathermap_metric_out"
        :label="_t('Metric (out)')"
        :list="metrics.metrics"
        :placeholder="_t('second metric (optional)')"
        :empty-hint="_t('No metrics available')"
      />
    </PropertyRow>

    <!--
      Weather colouring drives the stroke and skips the border, so the two
      colour fields would have no effect while it is on.
    -->
    <template v-if="!form.line_weather_color">
      <PropertyRow :label="_t('Line color')">
        <MapsColorInput
          v-model="form.line_color"
          :enable-label="_t('Use color')"
          default-color="#ffffff"
        />
      </PropertyRow>
      <PropertyRow :label="_t('Border color')">
        <MapsColorInput
          v-model="form.line_color_border"
          :enable-label="_t('Use color')"
          default-color="#000000"
        />
      </PropertyRow>
    </template>
    <PropertyRow :label="_t('Line width')">
      <CmkInput
        v-model="form.line_width"
        type="number"
        :min="1"
        :max="20"
        :placeholder="_t('auto')"
      />
    </PropertyRow>

    <template v-if="hasOwnCoordinates">
      <PropertyRow :label="_t('Start X')">
        <CmkInput v-model="form.x" type="number" min="0" max="10000" />
      </PropertyRow>
      <PropertyRow :label="_t('Start Y')">
        <CmkInput v-model="form.y" type="number" min="0" max="10000" />
      </PropertyRow>
      <PropertyRow :label="_t('End X')">
        <CmkInput v-model="form.x2" type="number" min="0" max="10000" />
      </PropertyRow>
      <PropertyRow :label="_t('End Y')">
        <CmkInput v-model="form.y2" type="number" min="0" max="10000" />
      </PropertyRow>
    </template>

    <PropertyRow :label="_t('Show label')">
      <CmkCheckbox v-model="form.label.show" />
    </PropertyRow>
    <PropertyRow v-if="form.label.show" :label="_t('Line label')">
      <CmkInput v-model="form.label.text" field-size="fill" />
    </PropertyRow>
  </PropertySection>
</template>

<style scoped>
.maps-line-section__note {
  margin: 0;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
