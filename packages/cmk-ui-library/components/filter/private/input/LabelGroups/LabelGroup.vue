<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { LabelGroupItem } from './types'

const { _t } = usei18n()

const autocompleter = computed(
  () =>
    ({
      fetch_method: 'rest_autocomplete',
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
  <div class="cmk-label-group">
    <div class="cmk-label-group__simple-list">
      <div v-for="(_item, index) in model" :key="index" class="cmk-label-group__simple-list-item">
        <div class="cmk-label-group__simple-list-item-content">
          <div class="cmk-label-group__item">
            <div class="cmk-label-group__item-operator">
              <CmkDropdown
                :options="{ type: 'fixed', suggestions: getOperatorChoices(index) }"
                :label="_t('Operator')"
                :model-value="getCurrentOperatorValue(index)"
                @update:model-value="(value: string | null) => updateOperator(index, value)"
              />
            </div>
            <div class="cmk-label-group__item-label">
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
        <button
          v-if="canRemove(index)"
          class="cmk-label-group__simple-list-item-remove"
          @click="tryDelete(index)"
        >
          <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
        </button>
        <div v-else class="cmk-label-group__spacer"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cmk-label-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.cmk-label-group__simple-list {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--dimension-4);
  align-items: center;
}

.cmk-label-group__simple-list-item {
  display: contents;
}

.cmk-label-group__simple-list-item-content {
  display: contents;
}

.cmk-label-group__simple-list-item-remove {
  width: var(--dimension-7);
  height: var(--dimension-7);
  color: var(--font-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  margin: 0;
  padding: var(--dimension-4) var(--dimension-5);
}

.cmk-label-group__spacer {
  width: var(--dimension-10);
  height: var(--dimension-7);
}

.cmk-label-group__item {
  display: contents;
}

.cmk-label-group__item-operator {
  width: 70px;
}
</style>
