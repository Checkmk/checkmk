<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  GraphOptionUnitCustomNotation,
  GraphOptionUnitCustomNotationWithSymbol,
  GraphOptionUnitCustomPrecision,
  GraphOptions
} from 'cmk-shared-typing/typescript/graph_designer'
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import type { Suggestion } from '@/components/suggestions'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { extractUnitFields } from '../converters'

const { _t } = usei18n()

const props = defineProps<{
  graph_options: GraphOptions
}>()

const { unitType, notation, symbol, precisionType, precisionDigits } = extractUnitFields(
  props.graph_options?.unit ?? 'first_entry_with_unit'
)

const dataUnitChoice = ref(unitType)
const unitChoiceSuggestions: Suggestion[] = [
  { name: 'custom', title: _t('Custom') },
  {
    name: 'first_entry_with_unit',
    title: _t('Use unit of first entry')
  }
]

const dataNotation = ref<GraphOptionUnitCustomNotationWithSymbol['type'] | 'time'>(notation)
const dataNotationSymbol = ref<string>(symbol)

const notationSuggestions: Suggestion[] = [
  { name: 'decimal', title: _t('Decimal') },
  { name: 'si', title: _t('SI') },
  { name: 'iec', title: _t('IEC') },
  {
    name: 'standard_scientific',
    title: _t('Standard scientific')
  },
  {
    name: 'engineering_scientific',
    title: _t('Engineering scientific')
  },
  { name: 'time', title: _t('Time') }
]

const dataPrecisionRoundingMode = ref<GraphOptionUnitCustomPrecision['type']>(precisionType)
const dataPrecisionDigits = ref<number>(precisionDigits)
const precisionRoundingModeSuggestions: Suggestion[] = [
  { name: 'auto', title: _t('Auto') },
  { name: 'strict', title: _t('Strict') }
]

const emit = defineEmits<{
  (
    e: 'update:unit',
    value:
      | 'first_entry_with_unit'
      | {
          notation:
            | 'time'
            | { type: GraphOptionUnitCustomNotationWithSymbol['type']; symbol: string }
          precision: { type: GraphOptionUnitCustomPrecision['type']; digits: number }
        }
  ): void
}>()

watch(
  [
    dataUnitChoice,
    dataNotation,
    dataNotationSymbol,
    dataPrecisionRoundingMode,
    dataPrecisionDigits
  ],
  () => {
    const unit:
      | 'first_entry_with_unit'
      | {
          notation: GraphOptionUnitCustomNotation
          precision: GraphOptionUnitCustomPrecision
        } =
      dataUnitChoice.value === 'custom'
        ? dataNotation.value === 'time'
          ? {
              notation: 'time',
              precision: {
                type: dataPrecisionRoundingMode.value,
                digits: dataPrecisionDigits.value
              }
            }
          : {
              notation: {
                type: dataNotation.value,
                symbol: dataNotationSymbol.value
              },
              precision: {
                type: dataPrecisionRoundingMode.value,
                digits: dataPrecisionDigits.value
              }
            }
        : 'first_entry_with_unit'

    emit('update:unit', unit)
  }
)
</script>
<template>
  <div class="gd-unit-editor__row">
    <div class="gd-unit-editor__legend">
      <CmkParagraph>
        {{ _t('Unit') }}
        <span class="dots">{{ Array(200).join('.') }}</span>
      </CmkParagraph>
    </div>
    <div class="gd-unit-editor__content">
      <CmkDropdown
        v-model:selected-option="dataUnitChoice"
        :options="{ type: 'fixed', suggestions: unitChoiceSuggestions }"
        :label="_t('Custom')"
      />

      <CmkIndent v-if="dataUnitChoice === 'custom'">
        <div>
          <CmkLabel>
            {{ _t('Notation') }}
          </CmkLabel>
          <CmkIndent>
            <CmkDropdown
              v-model:selected-option="dataNotation"
              :options="{ type: 'fixed', suggestions: notationSuggestions }"
              :label="_t('Notation')"
            />
            <CmkIndent v-if="dataNotation !== 'time'">
              <CmkInput v-model="dataNotationSymbol" placeholder="symbol" type="text" />
            </CmkIndent>
          </CmkIndent>
          <CmkLabel>
            {{ _t('Precision') }}
          </CmkLabel>
          <CmkIndent>
            <div>
              <div class="gd-unit-editor__label-element-row">
                <CmkLabel>
                  {{ _t('Rounding mode') }}
                </CmkLabel>
                <CmkDropdown
                  v-model:selected-option="dataPrecisionRoundingMode"
                  :options="{ type: 'fixed', suggestions: precisionRoundingModeSuggestions }"
                  :label="_t('Custom')"
                />
              </div>
              <CmkSpace size="medium" />
              <div class="gd-unit-editor__label-element-row">
                <CmkLabel>
                  {{ _t('Digits') }}
                </CmkLabel>
                <CmkInput v-model="dataPrecisionDigits" type="number" />
              </div>
            </div>
          </CmkIndent>
        </div>
      </CmkIndent>
    </div>
  </div>
</template>

<style scoped>
.gd-unit-editor__row {
  display: flex;
  align-items: first baseline;
  width: 20%;
  padding: 0 0 8px 8px;
}

.gd-unit-editor__legend {
  min-width: 240px;
  margin-right: 1rem;
  white-space: nowrap;
  overflow: hidden;
}

.gd-unit-editor__content {
  flex: 1;
  min-width: 450px;
}

.gd-unit-editor__label-element-row {
  display: flex;
  align-items: center;
  gap: 2rem;
}
</style>
