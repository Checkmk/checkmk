<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  GraphOptionExplicitVerticalRangeBoundaries,
  GraphOptions
} from 'cmk-shared-typing/typescript/graph_designer'
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { extractExplicitVerticalRangeBounds } from '../converters'

const { _t } = usei18n()

const props = defineProps<{
  graph_options: GraphOptions
}>()

const { lower, upper } = extractExplicitVerticalRangeBounds(
  props.graph_options?.explicit_vertical_range ?? 'auto'
)
const dataExplicitVerticalRangeLower = ref<number>(lower ?? 1.0)
const dataExplicitVerticalRangeUpper = ref<number>(upper ?? 2.0)

const dataExplicitVerticalRange = ref<string>(
  props.graph_options?.explicit_vertical_range === 'auto' ? 'auto' : 'explicit'
)
const explicitVerticalRangeSuggestions: Suggestion[] = [
  { name: 'auto', title: _t('Auto') },
  { name: 'explicit', title: _t('Explicit range') }
]

const validateLower = (value: number) => {
  return value > dataExplicitVerticalRangeUpper.value ? ['Must be less than upper bound'] : []
}

const validateUpper = (value: number) => {
  return value < dataExplicitVerticalRangeLower.value ? ['Must be more than lower bound'] : []
}

const emit = defineEmits<{
  (
    e: 'update:explicitVerticalRange',
    value: GraphOptionExplicitVerticalRangeBoundaries | 'auto'
  ): void
}>()

watch(
  [dataExplicitVerticalRange, dataExplicitVerticalRangeLower, dataExplicitVerticalRangeUpper],
  () => {
    const explicitVerticalRange =
      dataExplicitVerticalRange.value === 'auto'
        ? 'auto'
        : {
            lower: dataExplicitVerticalRangeLower.value,
            upper: dataExplicitVerticalRangeUpper.value
          }

    emit('update:explicitVerticalRange', explicitVerticalRange)
  }
)
</script>
<template>
  <div class="gd-explicit-vertical-range-editor__row">
    <div class="gd-explicit-vertical-range-editor__legend">
      <CmkParagraph>
        {{ _t('Explicit range') }}
        <span class="dots">{{ Array(200).join('.') }}</span>
      </CmkParagraph>
    </div>
    <div class="gd-explicit-vertical-range-editor__content">
      <CmkDropdown
        v-model:selected-option="dataExplicitVerticalRange"
        :options="{ type: 'fixed', suggestions: explicitVerticalRangeSuggestions }"
        :label="_t('Strict')"
      />
      <CmkIndent v-if="dataExplicitVerticalRange === 'explicit'">
        <div>
          <div class="gd-explicit-vertical-range-editor__label-element-row">
            <CmkLabel>
              {{ _t('Lower') }}
            </CmkLabel>
            <CmkInput
              v-model="dataExplicitVerticalRangeLower"
              type="number"
              :validators="[validateLower]"
            />
          </div>
          <CmkSpace size="medium" />
          <div class="gd-explicit-vertical-range-editor__label-element-row">
            <CmkLabel>
              {{ _t('Upper') }}
            </CmkLabel>
            <CmkInput
              v-model="dataExplicitVerticalRangeUpper"
              type="number"
              :validators="[validateUpper]"
            />
          </div>
          <CmkSpace size="medium" />
        </div>
      </CmkIndent>
    </div>
  </div>
</template>
<style scoped>
.gd-explicit-vertical-range-editor__row {
  display: flex;
  align-items: first baseline;
  width: 20%;
  padding: 0 0 8px 8px;
}

.gd-explicit-vertical-range-editor__legend {
  min-width: 240px;
  margin-right: 1rem;
  white-space: nowrap;
  overflow: hidden;
}

.gd-explicit-vertical-range-editor__content {
  flex: 1;
  min-width: 450px;
}

.gd-explicit-vertical-range-editor__label-element-row {
  display: flex;
  align-items: center;
  gap: 2rem;
}
</style>
