<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  GraphOptionExplicitVerticalRangeBoundaries,
  GraphOptionUnitCustom,
  GraphOptions
} from 'cmk-shared-typing/typescript/graph_designer'
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import ExplicitVerticalRangeEditor from '@/graph-designer/components/ExplicitVerticalRangeEditor.vue'
import UnitEditor from '@/graph-designer/components/UnitEditor.vue'

const { _t } = usei18n()

const props = defineProps<{
  graph_options: GraphOptions
}>()

const emit = defineEmits<{
  (e: 'update:graphOptions', value: GraphOptions): void
}>()

const dataUnit = ref(props.graph_options?.unit ?? 'first_entry_with_unit')

function onUnitChange(value: 'first_entry_with_unit' | GraphOptionUnitCustom) {
  dataUnit.value = value
}

const dataExplicitVerticalRange = ref<'auto' | GraphOptionExplicitVerticalRangeBoundaries>(
  props.graph_options?.explicit_vertical_range ?? 'auto'
)
function onExplicitVerticalRangeChange(value: 'auto' | GraphOptionExplicitVerticalRangeBoundaries) {
  dataExplicitVerticalRange.value = value
}

const dataOmitZeroMetrics = ref<boolean>(false)

watch(dataUnit, () => {
  emit('update:graphOptions', {
    ...props.graph_options,
    unit: dataUnit.value
  })
})

watch(dataExplicitVerticalRange, () => {
  emit('update:graphOptions', {
    ...props.graph_options,
    explicit_vertical_range: dataExplicitVerticalRange.value
  })
})

watch(dataOmitZeroMetrics, () => {
  emit('update:graphOptions', {
    ...props.graph_options,
    omit_zero_metrics: dataOmitZeroMetrics.value
  })
})
</script>

<template>
  <UnitEditor :graph_options="props.graph_options" @update:unit="onUnitChange" />
  <ExplicitVerticalRangeEditor
    :graph_options="props.graph_options"
    @update:explicit-vertical-range="onExplicitVerticalRangeChange"
  />
  <div class="gd-graph-options-editor__row">
    <div class="gd-graph-options-editor__legend">
      <CmkParagraph>
        {{ _t('Graph metrics with all zero values') }}
        <span class="dots">{{ Array(200).join('.') }}</span>
      </CmkParagraph>
    </div>
    <div class="gd-graph-options-editor__content">
      <CmkCheckbox v-model="dataOmitZeroMetrics" />
    </div>
  </div>
</template>
<style scoped>
.gd-graph-options-editor__row {
  display: flex;
  align-items: first baseline;
  width: 20%;
  padding-left: 8px;
}

.gd-graph-options-editor__legend {
  min-width: 240px;
  margin-right: 1rem;
  white-space: nowrap;
  overflow: hidden;
}

.gd-graph-options-editor__content {
  flex: 1;
  min-width: 450px;
}
</style>
