<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkList from '@/components/CmkList'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import {
  type ConditionChoicesValue,
  type ConditionGroup,
  type Condition
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { immediateWatch } from '@/lib/watch'
import { computed, ref, watch } from 'vue'
import { type OperatorI18n, type Operator } from './utils'

const props = defineProps<{
  data: ConditionChoicesValue
  group: ConditionGroup
  i18n: {
    add_condition_label: string
  } & OperatorI18n
}>()

const FILTER_SHOW_THRESHOLD = 5

if (props.group.conditions.length === 0) {
  throw new Error('Invalid group')
}
const operatorIsMultiSelect = (operator: Operator) =>
  operator === 'oper_or' || operator === 'oper_nor'

const selectedOperator = ref<Operator>('oper_eq')
const selectedSingleValue = ref<string>(props.group.conditions[0]!.name)
const selectedMultiValue = ref<string[]>([props.group.conditions[0]!.name])

const remainingConditions = ref<Condition[]>(props.group.conditions)

immediateWatch(
  () => props.data,
  (data) => {
    const operator = Object.keys(data.value)[0] as Operator
    selectedOperator.value = operator
    if (operatorIsMultiSelect(operator)) {
      selectedMultiValue.value = Object.values(data.value)[0] as string[]
      selectedSingleValue.value = props.group.conditions[0]!.name
    } else {
      selectedSingleValue.value = Object.values(data.value)[0] as string
      selectedMultiValue.value = [props.group.conditions[0]!.name]
    }
    remainingConditions.value = props.group.conditions.filter(
      ({ name }) => !selectedMultiValue.value.includes(name)
    )
  }
)

const operatorChoices = computed<{ name: Operator; title: string }[]>(() => {
  if (props.group.conditions.length > 1) {
    return [
      { name: 'oper_eq', title: props.i18n.eq_operator },
      { name: 'oper_ne', title: props.i18n.ne_operator },
      { name: 'oper_or', title: props.i18n.or_operator },
      { name: 'oper_nor', title: props.i18n.nor_operator }
    ]
  }
  return [
    { name: 'oper_eq', title: props.i18n.eq_operator },
    { name: 'oper_ne', title: props.i18n.ne_operator }
  ]
})

const allValueChoices = computed(() => {
  return props.group.conditions.map((condition) => {
    return { name: condition.name, title: condition.title }
  })
})

const emit = defineEmits<{
  update: [value: ConditionChoicesValue]
}>()

function updateValue(operator: Operator, value: string | string[] | null) {
  emit('update', {
    group_name: props.data.group_name,
    value: {
      [operator]: value
    } as { oper_eq: string } | { oper_ne: string } | { oper_or: string[] } | { oper_nor: string[] }
  })
}

function addMultiValue() {
  selectedMultiValue.value.push(remainingConditions.value[0]!.name)
  updateValue(selectedOperator.value, selectedMultiValue.value)
  return true
}

function deleteMultiValue(index: number) {
  selectedMultiValue.value.splice(index, 1)
  updateValue(selectedOperator.value, selectedMultiValue.value)
  return true
}

function updateMultiValue(index: number, value: string) {
  selectedMultiValue.value[index] = value
  updateValue(selectedOperator.value, selectedMultiValue.value)
}

watch(selectedOperator, (operator) => {
  if (operatorIsMultiSelect(operator)) {
    if (selectedMultiValue.value.some((v) => v === null)) {
      return
    }
    updateValue(operator, selectedMultiValue.value as string[])
  } else {
    updateValue(operator, selectedSingleValue.value)
  }
})
</script>

<template>
  {{ group.title }}
  <CmkDropdown
    v-model:selected-option="selectedOperator"
    :options="operatorChoices"
    :show-filter="false"
    :label="props.i18n.choose_operator"
  />
  <CmkSpace :size="'small'" />
  <template v-if="allValueChoices.length === 1">
    {{ allValueChoices[0]!.title }}
  </template>
  <template v-else-if="operatorIsMultiSelect(selectedOperator)">
    <CmkList
      :items-props="{ selectedValue: selectedMultiValue }"
      :add="{
        show: remainingConditions.length > 0,
        tryAdd: addMultiValue,
        label: props.i18n.add_condition_label
      }"
      :try-delete="deleteMultiValue"
      :orientation="'horizontal'"
    >
      <template #item-props="{ index, selectedValue }">
        <CmkDropdown
          :selected-option="selectedValue"
          :options="[
            ...props.group.conditions
              .filter(({ name }) => name === selectedValue)
              .map((condition) => ({
                name: condition.name,
                title: condition.title
              })),
            ...remainingConditions.map((condition) => ({
              name: condition.name,
              title: condition.title
            }))
          ]"
          :show-filter="remainingConditions.length > FILTER_SHOW_THRESHOLD - 1"
          :label="props.i18n.choose_condition"
          @update:selected-option="(value) => updateMultiValue(index, value!)"
        />
      </template>
    </CmkList>
  </template>
  <template v-else>
    <CmkDropdown
      :selected-option="selectedSingleValue"
      :options="allValueChoices"
      :show-filter="allValueChoices.length > FILTER_SHOW_THRESHOLD"
      :label="props.i18n.choose_condition"
      @update:selected-option="(value) => updateValue(selectedOperator, value)"
    />
  </template>
</template>
