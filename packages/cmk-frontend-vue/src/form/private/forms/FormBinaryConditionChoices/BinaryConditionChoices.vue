<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type * as typing from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Ref, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkSpace from '@/components/CmkSpace.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'
import { type ValidationMessages } from '@/form/private/validation'

import { firstOperatorSuggestions, operatorSuggestions } from './suggestions'

const { _t } = usei18n()

const props = defineProps<{
  data: typing.BinaryConditionChoicesItem[]
  spec: typing.BinaryConditionChoices
  backendValidation: ValidationMessages
}>()

const data: Ref<typing.BinaryConditionChoicesItem[]> = ref(props.data)
const defaultOperator: Ref<'and' | 'or' | 'not'> = ref('and')
const defaultLabel = ref<string | null>(null)

const getUsedLabels = (): (string | null)[] => data.value.map((g) => g.label)
const filterUnusedLabels = (s: { name: string | null }): boolean =>
  !getUsedLabels().includes(s.name)

function removeItem(itemIndex: number) {
  data.value.splice(itemIndex, 1)
  if (data.value[0] !== undefined && data.value[0].operator === 'or') {
    data.value[0].operator = 'and'
  }
}

function displayFirstOperators() {
  return data.value.length === 0
}

function addItem() {
  if (defaultOperator.value && defaultLabel.value) {
    data.value.push({ operator: defaultOperator.value, label: defaultLabel.value })
    defaultOperator.value = 'and'
    defaultLabel.value = null
  }
}
</script>

<template>
  <div class="form-binary-condition-choices__label-group">
    <table class="form-binary-condition-choices__label-group">
      <tbody>
        <tr v-for="(item, itemIndex) in data" :key="itemIndex">
          <td v-if="itemIndex === 0">
            <CmkDropdown
              v-model:selected-option="item.operator"
              :options="{
                type: 'fixed',
                suggestions: firstOperatorSuggestions
              }"
              :input-hint="_t('Select operator')"
              :no-elements-text="_t('Add')"
              :width="'fill'"
              :label="_t('Add')"
            />
          </td>
          <td v-else>
            <CmkDropdown
              v-model:selected-option="item.operator"
              :options="{
                type: 'fixed',
                suggestions: operatorSuggestions
              }"
              :input-hint="_t('Select operator')"
              :no-elements-text="_t('Add')"
              :width="'fill'"
              :label="_t('Add')"
            />
          </td>
          <td>
            <FormAutocompleter
              v-model="item.label"
              :autocompleter="props.spec.autocompleter"
              :placeholder="_t('Select label')"
              :filter="(s) => item.label === s.name || !getUsedLabels().includes(s.name)"
            />
          </td>
          <td v-if="item.label !== null">
            <CmkSpace :size="'small'" />
            <CmkIconButton
              name="close"
              :size="'small'"
              :aria-label="_t('Remove item')"
              @click="() => removeItem(itemIndex)"
            />
          </td>
        </tr>
        <tr>
          <td v-if="displayFirstOperators()">
            <CmkDropdown
              v-model:selected-option="defaultOperator"
              :options="{
                type: 'fixed',
                suggestions: firstOperatorSuggestions
              }"
              :input-hint="_t('Select operator')"
              :no-elements-text="_t('Add')"
              :width="'fill'"
              :label="_t('Add')"
            />
          </td>
          <td v-else>
            <CmkDropdown
              v-model:selected-option="defaultOperator"
              :options="{
                type: 'fixed',
                suggestions: operatorSuggestions
              }"
              :input-hint="_t('Select operator')"
              :no-elements-text="_t('Add')"
              :width="'fill'"
              :label="_t('Add')"
            />
          </td>
          <td>
            <FormAutocompleter
              v-model="defaultLabel"
              :autocompleter="props.spec.autocompleter"
              :placeholder="_t('Select label')"
              :filter="filterUnusedLabels"
              @update:model-value="addItem()"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
div.form-binary-condition-choices__label-group {
  display: inline-block;
  padding: 2px;
  background-color: var(--default-tooltip-background-color);
  border: 1px solid var(--default-form-element-border-color);
}

table.form-binary-condition-choices__label-group {
  border-spacing: var(--spacing-half);
}
</style>
