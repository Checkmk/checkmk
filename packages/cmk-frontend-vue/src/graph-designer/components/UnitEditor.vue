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
  GraphOptions,
  I18N
} from 'cmk-shared-typing/typescript/graph_designer'
import { ref, watch } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import type { Suggestion } from '@/components/suggestions'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { extractUnitFields } from '../converters'

const props = defineProps<{
  graph_options: GraphOptions
  i18n: I18N
}>()

const { unitType, notation, symbol, precisionType, precisionDigits } = extractUnitFields(
  props.graph_options?.unit ?? 'first_entry_with_unit'
)

const dataUnitChoice = ref(unitType)
const unitChoiceSuggestions: Suggestion[] = [
  { name: 'custom', title: props.i18n.unit_custom as TranslatedString },
  {
    name: 'first_entry_with_unit',
    title: props.i18n.unit_first_entry_with_unit as TranslatedString
  }
]

const dataNotation = ref<GraphOptionUnitCustomNotationWithSymbol['type'] | 'time'>(notation)
const dataNotationSymbol = ref<string>(symbol)

const notationSuggestions: Suggestion[] = [
  { name: 'decimal', title: props.i18n.unit_custom_notation_decimal as TranslatedString },
  { name: 'si', title: props.i18n.unit_custom_notation_si as TranslatedString },
  { name: 'iec', title: props.i18n.unit_custom_notation_iec as TranslatedString },
  {
    name: 'standard_scientific',
    title: props.i18n.unit_custom_notation_standard_scientific as TranslatedString
  },
  {
    name: 'engineering_scientific',
    title: props.i18n.unit_custom_notation_engineering_scientific as TranslatedString
  },
  { name: 'time', title: props.i18n.unit_custom_notation_time as TranslatedString }
]

const dataPrecisionRoundingMode = ref<GraphOptionUnitCustomPrecision['type']>(precisionType)
const dataPrecisionDigits = ref<number>(precisionDigits)
const precisionRoundingModeSuggestions: Suggestion[] = [
  { name: 'auto', title: props.i18n.unit_custom_precision_type_auto as TranslatedString },
  { name: 'strict', title: props.i18n.unit_custom_precision_type_strict as TranslatedString }
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
        {{ props.i18n.unit }}
        <span class="dots">{{ Array(200).join('.') }}</span>
      </CmkParagraph>
    </div>
    <div class="gd-unit-editor__content">
      <CmkDropdown
        v-model:selected-option="dataUnitChoice"
        :options="{ type: 'fixed', suggestions: unitChoiceSuggestions }"
        :label="props.i18n.unit_custom as TranslatedString"
      />

      <CmkIndent v-if="dataUnitChoice === 'custom'">
        <div>
          <CmkLabel>
            {{ props.i18n.unit_custom_notation }}
          </CmkLabel>
          <CmkIndent>
            <CmkDropdown
              v-model:selected-option="dataNotation"
              :options="{ type: 'fixed', suggestions: notationSuggestions }"
              :label="props.i18n.unit_custom_notation as TranslatedString"
            />
            <CmkIndent v-if="dataNotation !== 'time'">
              <CmkInput v-model="dataNotationSymbol" placeholder="symbol" type="text" />
            </CmkIndent>
          </CmkIndent>
          <CmkLabel>
            {{ props.i18n.unit_custom_precision }}
          </CmkLabel>
          <CmkIndent>
            <div>
              <div class="gd-unit-editor__label-element-row">
                <CmkLabel>
                  {{ props.i18n.unit_custom_precision_type }}
                </CmkLabel>
                <CmkDropdown
                  v-model:selected-option="dataPrecisionRoundingMode"
                  :options="{ type: 'fixed', suggestions: precisionRoundingModeSuggestions }"
                  :label="props.i18n.unit_custom as TranslatedString"
                />
              </div>
              <CmkSpace size="medium" />
              <div class="gd-unit-editor__label-element-row">
                <CmkLabel>
                  {{ props.i18n.unit_custom_precision_digits }}
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
