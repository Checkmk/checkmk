<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import FormEdit from '@/form/components/FormEdit.vue'
import type { List } from '@/form/components/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import {
  groupIndexedValidations,
  validateValue,
  type ValidationMessages
} from '@/form/components/utils/validation'
import CmkList from '@/components/CmkList.vue'

const props = defineProps<{
  spec: List
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })

const validation = ref<Array<string>>([])
const elementValidation = ref<Array<ValidationMessages>>([])

function initialize(newBackendData: unknown[]) {
  validation.value.splice(0)
  elementValidation.value.splice(0)
  newBackendData.forEach(() => {
    elementValidation.value.push([] as ValidationMessages)
  })
}

watch(
  [data, () => props.backendValidation],
  ([newBackendData, newBackendValidation]) => {
    initialize(newBackendData)
    setValidation(newBackendValidation)
  },
  { immediate: true }
)

function setValidation(newBackendValidation: ValidationMessages) {
  const [_listValidations, _elementValidations] = groupIndexedValidations(
    newBackendValidation,
    data.value.length
  )
  validation.value = _listValidations
  Object.entries(_elementValidations).forEach(([i, value]) => {
    elementValidation.value[i as unknown as number] = value
  })
}

function _validateList() {
  validation.value = []
  validateValue(data.value, props.spec.validators!).forEach((error) => {
    validation.value.push(error)
  })
}

function addElement(index: number) {
  data.value[index] = JSON.parse(JSON.stringify(props.spec.element_default_value))
  elementValidation.value[index] = []
  _validateList()
}

function deleteElement(index: number) {
  data.value.splice(index, 1)
  elementValidation.value.splice(index, 1)
  _validateList()
}

function updateElementData(newValue: unknown, index: number) {
  data.value[index] = newValue
}

function reorderElements(order: number[]) {
  data.value = order.map((index) => data.value[index])
  elementValidation.value = order.map((index) => elementValidation.value[index]!)
}
</script>

<template>
  <CmkList
    :items-props="{ data, elementValidation }"
    :draggable="props.spec.editable_order ? { onReorder: reorderElements } : null"
    :on-add="addElement"
    :on-delete="deleteElement"
    :i18n="{
      addElementLabel: props.spec.add_element_label
    }"
  >
    <template #item-props="{ index, data: itemData, elementValidation: itemElementValidation }">
      <FormEdit
        :data="itemData"
        :spec="spec.element_template"
        :backend-validation="itemElementValidation"
        @update:data="(new_value: unknown) => updateElementData(new_value, index)"
      ></FormEdit>
    </template>
  </CmkList>
  <FormValidation :validation="validation"></FormValidation>
</template>
