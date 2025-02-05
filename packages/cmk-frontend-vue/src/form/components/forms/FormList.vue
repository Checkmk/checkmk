<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'
import type { List } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import { type ValidationMessages } from '@/form/components/utils/validation'
import CmkList from '@/components/CmkList'
import { useFormEditDispatcher } from '@/form/private'
import formListActions from '@/form/components/forms/utils/formListActions'

const props = defineProps<{
  spec: List
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })

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

function reorderElements(order: number[]) {
  data.value = order.map((index) => data.value[index])
  elementValidation.value = order.map((index) => elementValidation.value[index]!)
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <span>
    <CmkList
      :items-props="{ itemData: data, itemElementValidation: elementValidation }"
      :draggable="props.spec.editable_order ? { onReorder: reorderElements } : null"
      :add="{
        show: true,
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
          :spec="spec.element_template"
          :backend-validation="itemElementValidation"
          @update:data="(new_value: unknown) => updateElementData(new_value, index)"
        />
      </template>
    </CmkList>
    <FormValidation :validation="validation"></FormValidation>
  </span>
</template>
