<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeMount, ref, watch } from 'vue'
import { useFormEditDispatcher } from '@/form/private'
import type { ListOfStrings } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import {
  groupIndexedValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'

const props = defineProps<{
  spec: ListOfStrings
  backendValidation: ValidationMessages
}>()

const backendData = defineModel<string[]>('data', { required: true })
const validation = ref<Array<string>>([])
type ElementIndex = number
const elementValidation = ref<Record<ElementIndex, ValidationMessages>>({})

watch(
  backendData,
  () => {
    checkAutoextend()
  },
  { deep: true }
)

function initialize(newBackendData: unknown[]) {
  validation.value.splice(0)
  elementValidation.value = {}
  for (const i in newBackendData) {
    elementValidation.value[i] = []
  }
  checkAutoextend()
}

onBeforeMount(() => {
  initialize(backendData)
  setValidation(props.backendValidation)
})
watch([backendData, () => props.backendValidation], ([newBackendData, newBackendValidation]) => {
  initialize(newBackendData)
  setValidation(newBackendValidation)
})

function setValidation(newBackendValidation: ValidationMessages) {
  const [_listValidations, _elementValidations] = groupIndexedValidations(
    newBackendValidation,
    backendData.value.length
  )
  validation.value = _listValidations
  elementValidation.value = _elementValidations
}

function checkAutoextend(): void {
  if (backendData.value[backendData.value.length - 1] === '') {
    return
  }
  backendData.value.push('')
  elementValidation.value[backendData.value.length - 1] = []
}

function onPaste(e: ClipboardEvent, index: number) {
  e.preventDefault()
  // Get pasted data via clipboard API
  const clipboardData = e.clipboardData
  if (clipboardData === null) {
    return
  }
  const pasted = clipboardData.getData('Text')
  // When pasting a string, trim separators and then split by the given separators
  const stripped = pasted.replace(new RegExp('^[;]+|[;]+$', 'g'), '')
  const entries = stripped.split(new RegExp('[;]+'))

  if (entries.length === 0) {
    return
  }
  // Add first entry to the current index
  // Note: This will fully overwrite the current value, no insert/extend of the existing value
  backendData.value[index] = entries[0]!

  for (let i = 1; i < entries.length; i++) {
    // Append new fields for the remaining entries
    if (backendData.value[backendData.value.length - 1] === '') {
      backendData.value[backendData.value.length - 1] = entries[i]!
    } else {
      backendData.value.push(entries[i]!)
    }
    elementValidation.value[backendData.value.length - 1] = []
  }
  checkAutoextend()
}
// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <table ref="tableRef" class="form-list-of-strings">
    <tbody>
      <template v-for="(_, index) in backendData" :key="index">
        <tr
          class="listof_element"
          :style="{ float: props.spec.layout === 'vertical' ? 'unset' : 'left' }"
          @paste="(event: ClipboardEvent) => onPaste(event, index)"
        >
          <td class="vlof_content">
            <FormEditDispatcher
              v-model:data="backendData[index]"
              :spec="spec.string_spec"
              :backend-validation="elementValidation[index]!"
            />
          </td>
        </tr>
      </template>
    </tbody>
  </table>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.form-list-of-strings {
  border-spacing: 2px 0;

  > tbody > .listof_element > .vlof_content {
    vertical-align: top;
    padding-bottom: 8px;
  }
}
</style>
