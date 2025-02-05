<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { type ValidationMessages } from '@/form/components/utils/validation'
import CmkList from '@/components/CmkList'
import formListActions from '@/form/components/forms/utils/formListActions'
import type { ListUniqueSelection } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useFormEditDispatcher } from '@/form/private'

const props = defineProps<{
  spec: ListUniqueSelection
  backendValidation: ValidationMessages
}>()

const data = defineModel<Array<string | [string, unknown]>>('data', { required: true })

const validation = ref<Array<string>>([])
const elementValidation = ref<Array<ValidationMessages>>([])

const { initialize, deleteElement, addElement, updateElementData, setValidation } = formListActions(
  props,
  data,
  validation,
  elementValidation
)

watch(
  [data, () => props.backendValidation],
  ([newBackendData, newBackendValidation]) => {
    initialize(newBackendData)
    setValidation(newBackendValidation)
  },
  { immediate: true }
)

function filteredElementTemplate(index: number) {
  return {
    ...props.spec.element_template,
    elements: props.spec.element_template.elements.filter((element) => {
      if (!props.spec.unique_selection_elements.includes(element['name'])) {
        return true
      }
      switch (props.spec.element_template.type) {
        case 'single_choice':
          return !data.value.some((name, idx) => name === element['name'] && idx !== index)
        case 'cascading_single_choice':
          return !data.value.some(([name], idx) => name === element['name'] && idx !== index)
      }
    })
  }
}

// eslint is unable to determine that switch covers all cases typescript does so.
// eslint-disable-next-line vue/return-in-computed-property
const usedKeys = computed(() => {
  switch (props.spec.element_template.type) {
    case 'single_choice':
      return data.value.map((name) => name)
    case 'cascading_single_choice':
      return data.value.map(([name]) => name)
  }
})

const showAddButton = computed(() => {
  if (props.spec.element_template.elements.length !== props.spec.unique_selection_elements.length) {
    return true
  }

  if (data.value.length === props.spec.unique_selection_elements.length) {
    return false
  }

  for (const element of props.spec.element_template.elements) {
    if (!usedKeys.value.includes(element['name'])) {
      return true
    }
  }
  return false
})

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <CmkList
    :items-props="{ itemData: data, itemElementValidation: elementValidation }"
    :add="{
      show: showAddButton,
      tryAdd: addElement,
      label: props.spec.add_element_label
    }"
    :try-delete="deleteElement"
    role="group"
    :aria-label="props.spec.title"
  >
    <template #item-props="{ index, itemData, itemElementValidation }">
      <FormEditDispatcher
        :data="itemData"
        :spec="filteredElementTemplate(index)"
        :backend-validation="itemElementValidation"
        @update:data="(new_value: unknown) => updateElementData(new_value, index)"
      />
    </template>
  </CmkList>
</template>
