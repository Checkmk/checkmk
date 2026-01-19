<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type * as typing from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIconButton from '@/components/CmkIconButton.vue'

import FormButton from '@/form/private/FormButton.vue'
import { type ValidationMessages } from '@/form/private/validation'

import BinaryConditionChoices from './BinaryConditionChoices.vue'
import { operatorSuggestions } from './suggestions'

const { _t } = usei18n()

const props = defineProps<{
  spec: typing.BinaryConditionChoices
  backendValidation: ValidationMessages
}>()

const data = defineModel<typing.BinaryConditionChoicesValue | null>('data', {
  required: true,
  default: null
})

function addGroup() {
  if (data.value === null) {
    data.value = []
  }
  data.value.push({ operator: 'and', label_group: [] })
}

function removeGroup(groupIndex: number) {
  if (data.value !== null) {
    data.value.splice(groupIndex, 1)
  }
}
</script>

<template>
  <div v-if="props.spec.conditions.length > 1">
    <table>
      <tbody>
        <tr v-for="(group, groupIndex) in data" :key="groupIndex">
          <td>
            <CmkIconButton
              name="close"
              :size="'small'"
              :aria-label="_t('Remove group')"
              @click="() => removeGroup(groupIndex)"
            />
          </td>
          <td v-if="groupIndex === 0" class="form-binary-condition-choices__first-line">
            {{ props.spec.label }}
          </td>
          <td v-else class="form-binary-condition-choices__first-line">
            <CmkDropdown
              v-model:selected-option="group.operator"
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
            <BinaryConditionChoices
              :data="group.label_group"
              :spec="props.spec"
              :backend-validation="props.backendValidation"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <FormButton @click="addGroup">{{ _t('Add to condition') }}</FormButton>
  </div>
  <div v-else>
    {{ _t('No labels') }}
  </div>
</template>

<style scoped>
td {
  padding-right: 10px;
}

td.form-binary-condition-choices__first-line {
  vertical-align: top;
  padding-top: 8px;
}
</style>
