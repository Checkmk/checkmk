<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How the object is drawn: as an icon, as plain text, or as a gadget reading one
of its metrics.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ImagePicker from '@/maps/image-library/components/ImagePicker.vue'
import type { ObjectMetrics } from '@/maps/map/edit/composables/useObjectMetrics'
import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'
import PropertySection from '@/maps/map/edit/properties/PropertySection.vue'
import type { ObjectForm } from '@/maps/map/edit/properties/objectForm'
import MapsSuggestionField from '@/maps/shared/components/MapsSuggestionField.vue'
import { GADGET_DEFAULT_SIZE } from '@/maps/utils/gadget'

const props = defineProps<{
  metrics: ObjectMetrics
  /** The map's own icon size, shown as the placeholder an object inherits. */
  mapIconSize?: number | null | undefined
}>()

const form = defineModel<ObjectForm>('form', { required: true })

const { _t } = usei18n()

const viewTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'icon', title: _t('Icon') },
    { name: 'text', title: _t('Text only') },
    { name: 'gadget', title: _t('Gadget') }
  ]
}))

const gadgetTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'gauge', title: _t('Gauge') },
    { name: 'bar', title: _t('Bar') },
    { name: 'trafficlight', title: _t('Traffic light') },
    { name: 'value', title: _t('Value') }
  ]
}))

const isGadget = computed(() => form.value.display.mode === 'gadget')

const sizePlaceholder = computed(() => {
  if (isGadget.value) {
    return untranslated(String(GADGET_DEFAULT_SIZE))
  }
  return props.mapIconSize !== null && props.mapIconSize !== undefined
    ? untranslated(String(props.mapIconSize))
    : _t('map default')
})
</script>

<template>
  <PropertySection :title="_t('Appearance')">
    <PropertyRow :label="_t('View type')">
      <CmkDropdown
        floating
        :model-value="form.display.mode"
        :options="viewTypeOptions"
        :label="_t('View type')"
        width="fill"
        @update:model-value="form.display.mode = ($event ?? 'icon') as typeof form.display.mode"
      />
    </PropertyRow>
    <PropertyRow :label="_t('Size')">
      <CmkInput
        v-model="form.display.image_size"
        type="number"
        min="1"
        max="512"
        :placeholder="sizePlaceholder"
      />
    </PropertyRow>

    <template v-if="isGadget">
      <PropertyRow :label="_t('Gadget type')">
        <CmkDropdown
          floating
          :model-value="form.display.gadget_type"
          :options="gadgetTypeOptions"
          :label="_t('Gadget type')"
          width="fill"
          @update:model-value="form.display.gadget_type = $event ?? ''"
        />
      </PropertyRow>
      <PropertyRow :label="_t('Metric')">
        <MapsSuggestionField
          v-model="form.display.gadget_metric"
          :label="_t('Metric')"
          :list="metrics.metrics"
          :placeholder="_t('first metric')"
          :empty-hint="_t('No metrics available')"
        />
      </PropertyRow>
    </template>

    <PropertyRow v-else :label="_t('Custom icon')" tall>
      <ImagePicker v-model="form.display.image" />
    </PropertyRow>
  </PropertySection>
</template>
