<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

import type { LabelGroupItem } from './types'

const { _t } = usei18n()

const autocompleter = computed(
  () =>
    ({
      fetch_method: 'ajax_vs_autocomplete',
      data: {
        ident: 'label',
        params: {
          world: 'core',
          context: {
            group_labels: model.value.map((item) => item.label).filter((label) => label !== null)
          },
          strict: true,
          escape_regex: false
        }
      }
    }) as Autocompleter
)

const model = defineModel<LabelGroupItem[]>({
  default: () => [{ operator: 'and', label: null }]
})

const firstElementChoices = [
  { name: 'and', title: _t('is') },
  { name: 'not', title: _t('is not') }
]

const regularChoices = [
  { name: 'and', title: _t('and') },
  { name: 'or', title: _t('or') },
  { name: 'not', title: _t('not') }
]

function tryDelete(index: number) {
  if (!canRemove(index)) {
    return
  }

  const newValue = [...model.value]
  newValue.splice(index, 1)

  // Special handling: if we removed the first item, update the new first item's operator
  // to use the first element choices (defaulting to the first option)
  if (index === 0 && newValue.length > 0) {
    newValue[0]! = {
      label: newValue[0]!.label,
      operator: firstElementChoices[0]!.name
    }
  }

  model.value = newValue
  return true
}

function updateOperator(index: number, operator: string | null) {
  const newValue = [...model.value]
  newValue[index] = { label: newValue[index]!.label, operator: operator! }
  model.value = newValue
}

function updateLabel(index: number, label: string | null) {
  const newValue = [...model.value]
  newValue[index] = { operator: newValue[index]!.operator, label }
  if (label && index === model.value.length - 1) {
    const defaultOperator = regularChoices[0]!.name
    newValue.push({ operator: defaultOperator, label: null })
  }
  model.value = newValue
}

function getOperatorChoices(index: number) {
  return index === 0 ? firstElementChoices : regularChoices
}

function getCurrentOperatorValue(index: number): string {
  return model.value[index]!.operator
}

function getCurrentLabelValue(index: number): string | null {
  return model.value[index]?.label || null
}

function canRemove(index: number): boolean {
  return (
    model.value.length > 1 &&
    !(index === model.value.length - 1 && model.value[index]!.label === null)
  )
}

// Initialize with default value if empty
if (model.value.length === 0) {
  model.value = [{ operator: 'and', label: null }]
}
</script>

<template>
  <div class="label-group">
    <div class="simple-list">
      <div v-for="(_item, index) in model" :key="index" class="simple-list-item">
        <div class="simple-list-item__content">
          <div class="label-group-item">
            <div class="label-group-item__operator">
              <CmkDropdown
                :options="{ type: 'fixed', suggestions: getOperatorChoices(index) }"
                :label="_t('Operator')"
                :selected-option="getCurrentOperatorValue(index)"
                @update:selected-option="(value: string | null) => updateOperator(index, value)"
              />
            </div>
            <div class="label-group-item__label">
              <FormAutocompleter
                :model-value="getCurrentLabelValue(index)"
                :autocompleter="autocompleter"
                :placeholder="_t('Select label...')"
                :size="20"
                @update:model-value="(value: string | null) => updateLabel(index, value)"
              />
            </div>
          </div>
        </div>
        <button v-if="canRemove(index)" class="simple-list-item__remove" @click="tryDelete(index)">
          {{ untranslated('×') }}
        </button>
        <div v-else class="simple-list-item__spacer"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.label-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.simple-list {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--dimension-4);
  align-items: center;
}

.simple-list-item {
  display: contents;
}

.simple-list-item__content {
  display: contents;
}

.simple-list-item__remove {
  width: var(--dimension-8);
  height: var(--dimension-8);
  border: 1px solid #ccc;
  border-radius: var(--dimension-3);
  background: var(--font-color);
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--dimension-6);
  line-height: 1;
}

.simple-list-item__spacer {
  width: var(--dimension-8);
  height: var(--dimension-8);
}

.label-group-item {
  display: contents;
}

.label-group-item__operator {
  width: 70px;
}
</style>
