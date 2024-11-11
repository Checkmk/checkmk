<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSpace from '@/components/CmkSpace.vue'
import DropDown from '@/components/DropDown.vue'
import {
  type ConditionChoicesValue,
  type ConditionGroup
} from '@/form/components/vue_formspec_components'
import { immediateWatch } from '@/lib/watch'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  data: ConditionChoicesValue
  group: ConditionGroup
  i18n: {
    eq: string
    ne: string
    or: string
    nor: string
  }
}>()

if (props.group.conditions.length === 0) {
  throw new Error('Invalid group')
}

type KeysOfUnion<T> = T extends T ? keyof T : never
type Operator = KeysOfUnion<ConditionChoicesValue['value']>
const operatorIsMultiSelect = (operator: Operator) => operator === 'or' || operator === 'nor'

const selectedOperator = ref<Operator>('eq')
const selectedValue = ref<string>(props.group.conditions[0]!.name)

immediateWatch(
  () => props.data,
  (data) => {
    selectedOperator.value = Object.keys(data.value)[0] as Operator
    selectedValue.value = Object.values(data.value)[0]
  }
)

const operatorChoices = computed<{ name: Operator; title: string }[]>(() => {
  if (props.group.conditions.length > 1) {
    return [
      { name: 'eq', title: props.i18n.eq },
      { name: 'ne', title: props.i18n.ne },
      { name: 'or', title: props.i18n.or },
      { name: 'nor', title: props.i18n.nor }
    ]
  }
  return [
    { name: 'eq', title: props.i18n.eq },
    { name: 'ne', title: props.i18n.ne }
  ]
})

const valueChoices = computed(() => {
  return props.group.conditions.map((condition) => {
    return { name: condition.name, title: condition.title }
  })
})

const emit = defineEmits<{
  update: [value: ConditionChoicesValue]
}>()

watch([selectedOperator, selectedValue], ([operator, _value]) => {
  if (operator === undefined || _value === undefined) {
    return
  }
  emit('update', {
    group_name: props.data.group_name,
    value: {
      [operator]: operatorIsMultiSelect(operator) ? [_value] : _value
    } as { eq: string } | { ne: string } | { or: string[] } | { nor: string[] }
  })
})
</script>

<template>
  {{ group.title }}
  <DropDown v-model:selected-option="selectedOperator" :options="operatorChoices" />
  <CmkSpace :size="'small'" />
  <template v-if="valueChoices.length === 1">
    {{ valueChoices[0]!.title }}
  </template>
  <template v-else>
    <DropDown v-model:selected-option="selectedValue" :options="valueChoices" />
  </template>
</template>
