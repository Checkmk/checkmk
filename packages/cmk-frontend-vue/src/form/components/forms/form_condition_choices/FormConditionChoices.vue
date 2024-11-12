<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkList from '@/components/CmkList.vue'
import ConditionChoice from './ConditionChoice.vue'
import type * as typing from '@/form/components/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'
import DropDown from '@/components/DropDown.vue'
import { ref } from 'vue'

const props = defineProps<{
  spec: typing.ConditionChoices
  backendValidation: ValidationMessages
}>()

const data = defineModel<typing.ConditionChoicesValue[]>('data', { required: true })
const selectedConditionGroup = ref<string | null>(null)

function addElement() {
  if (selectedConditionGroup.value === null) {
    return
  }

  const group = props.spec.condition_groups[selectedConditionGroup.value]
  if (group === undefined || group.conditions.length === 0) {
    throw new Error('Invalid group')
  }
  data.value.push({
    group_name: selectedConditionGroup.value,
    value: { eq: group.conditions[0]!.name }
  })
  selectedConditionGroup.value = null
}

function deleteElement(index: number) {
  data.value.splice(index, 1)
}

function updateElementData(newValue: typing.ConditionChoicesValue, index: number) {
  data.value[index] = newValue
}
</script>

<template>
  <CmkList
    :items-props="{ data }"
    :on-add="addElement"
    :on-delete="deleteElement"
    :i18n="{
      addElementLabel: props.spec.i18n.add_condition_group_label
    }"
  >
    <template #item-props="{ index, data: itemData }">
      <ConditionChoice
        :data="itemData"
        :group="spec.condition_groups[data[index]!.group_name]!"
        :i18n="{
          eq: props.spec.i18n.eq_operator,
          ne: props.spec.i18n.ne_operator,
          or: props.spec.i18n.or_operator,
          nor: props.spec.i18n.nor_operator
        }"
        @update="(new_value: typing.ConditionChoicesValue) => updateElementData(new_value, index)"
      />
    </template>
  </CmkList>
  <DropDown
    v-model:selected-option="selectedConditionGroup"
    :options="
      Object.entries(spec.condition_groups)
        .filter(([name, _]) => data.find((v) => v.group_name === name) === undefined)
        .map(([name, value]) => ({ name, title: value.title }))
    "
  />
</template>
