<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkList from '@/components/CmkList'
import ConditionChoice from './ConditionChoice.vue'
import type * as typing from 'cmk-shared-typing/typescript/vue_formspec_components'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import { computed, ref } from 'vue'
import { immediateWatch } from '@/lib/watch'
import { required } from '@/form/private/requiredValidator'

const props = defineProps<{
  spec: typing.ConditionChoices
  backendValidation: ValidationMessages
}>()

const FILTER_SHOW_THRESHOLD = 5

const data = defineModel<typing.ConditionChoicesValue[]>('data', { required: true })
const selectedConditionGroup = ref<string | null>(null)

const validation = ref<Array<string>>([])
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    validation.value = newValidation.map((m) => m.message)
    newValidation.forEach((message) => {
      data.value = message.invalid_value as typing.ConditionChoicesValue[]
    })
  }
)

function addElement(selected: string | null) {
  if (selected === null) {
    return
  }

  const group = props.spec.condition_groups[selected]
  if (group === undefined || group.conditions.length === 0) {
    throw new Error('Invalid group')
  }
  data.value.push({
    group_name: selected,
    value: { oper_eq: group.conditions[0]!.name }
  })
  validation.value = validateValue(data.value, props.spec.validators)
  selectedConditionGroup.value = null
}

function deleteElement(index: number) {
  data.value.splice(index, 1)
  validation.value = validateValue(data.value, props.spec.validators)
}

function updateElementData(newValue: typing.ConditionChoicesValue, index: number) {
  data.value[index] = newValue
}

const remainingGroups = computed(() =>
  Object.entries(props.spec.condition_groups).filter(
    ([name, _]) => data.value.find((v) => v.group_name === name) === undefined
  )
)

const elementRequired = computed(() => {
  return props.spec.validators.some(required) && data.value.length === 0
})
</script>

<template>
  <CmkList
    :items-props="{ itemData: data }"
    :try-delete="
      (index) => {
        deleteElement(index)
        return true
      }
    "
  >
    <template #item-props="{ index, itemData }">
      <ConditionChoice
        :data="itemData"
        :group="spec.condition_groups[data[index]!.group_name]!"
        :i18n="{
          eq_operator: props.spec.i18n.eq_operator,
          ne_operator: props.spec.i18n.ne_operator,
          or_operator: props.spec.i18n.or_operator,
          nor_operator: props.spec.i18n.nor_operator,
          add_condition_label: props.spec.i18n.add_condition_label,
          choose_condition: props.spec.i18n.choose_condition,
          choose_operator: props.spec.i18n.choose_operator
        }"
        @update="(new_value: typing.ConditionChoicesValue) => updateElementData(new_value, index)"
      />
    </template>
  </CmkList>
  <CmkDropdown
    v-model:selected-option="selectedConditionGroup"
    :options="remainingGroups.map(([name, value]) => ({ name, title: value.title }))"
    :input-hint="spec.i18n.select_condition_group_to_add"
    :show-filter="remainingGroups.length > FILTER_SHOW_THRESHOLD"
    :required-text="elementRequired ? spec.i18n_base.required : ''"
    :no-elements-text="spec.i18n.no_more_condition_groups_to_add"
    :label="spec.i18n.select_condition_group_to_add"
    @update:selected-option="addElement"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
