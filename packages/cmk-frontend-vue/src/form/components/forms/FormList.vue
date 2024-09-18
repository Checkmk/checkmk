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

const props = defineProps<{
  spec: List
  backendValidation: ValidationMessages
}>()

const backendData = defineModel<unknown[]>('data', { required: true })

type ElementIndex = number
const data = ref<Record<ElementIndex, unknown>>({})
const validation = ref<Array<string>>([])
const elementValidation = ref<Record<ElementIndex, ValidationMessages>>({})
const frontendOrder = ref<ElementIndex[]>([])
const newElementIndex = ref<ElementIndex>(0)

function initialize(newBackendData: unknown[]) {
  data.value = {}
  validation.value.splice(0)
  elementValidation.value = {}
  frontendOrder.value.splice(0)
  newBackendData.forEach((value, i) => {
    data.value[i] = value
    elementValidation.value[i] = []
    frontendOrder.value.push(i)
  })
  newElementIndex.value = newBackendData.length
}

watch(
  [backendData, () => props.backendValidation],
  ([newBackendData, newBackendValidation]) => {
    initialize(newBackendData)
    setValidation(newBackendValidation)
  },
  { immediate: true }
)

function setValidation(newBackendValidation: ValidationMessages) {
  const [_listValidations, _elementValidations] = groupIndexedValidations(
    newBackendValidation,
    backendData.value.length
  )
  validation.value = _listValidations
  elementValidation.value = _elementValidations
}

let tableRef = ref<HTMLTableElement | null>(null)

function dragStart(event: DragEvent) {
  ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.add('dragging')
}

function dragEnd(event: DragEvent) {
  ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.remove('dragging')
}

function dragging(event: DragEvent) {
  if (tableRef.value == null || event.clientY == 0) {
    return
  }
  const tableChildren = [...tableRef.value!.children]
  const draggedRow = (event.target! as HTMLImageElement).closest('tr')!
  const draggedIndex = tableChildren.indexOf(draggedRow)

  const yCoords = event.clientY
  function siblingMiddlePoint(sibling: Element) {
    const siblingRect = sibling.getBoundingClientRect()
    return siblingRect.top + siblingRect.height / 2
  }

  let targetIndex = -1
  let previous: null | undefined | Element = draggedRow.previousElementSibling
  while (previous && yCoords < siblingMiddlePoint(previous)) {
    targetIndex = tableChildren.indexOf(previous)
    previous = tableRef.value!.children[targetIndex - 1]
  }

  let next: null | undefined | Element = draggedRow.nextElementSibling
  while (next && yCoords > siblingMiddlePoint(next)) {
    targetIndex = tableChildren.indexOf(next)
    next = tableRef.value!.children[targetIndex + 1]
  }

  if (draggedIndex === targetIndex || targetIndex === -1) {
    return
  }
  const movedEntry = frontendOrder.value.splice(draggedIndex, 1)[0]!
  frontendOrder.value.splice(targetIndex, 0, movedEntry)
  sendDataUpstream()
}

function validateList() {
  validation.value.splice(0)
  validateValue(backendData.value, props.spec.validators!).forEach((error) => {
    validation.value.push(error)
  })
}

function removeElement(index: ElementIndex) {
  frontendOrder.value.splice(frontendOrder.value.indexOf(index), 1)
  sendDataUpstream()
  validateList()
}

function addElement() {
  data.value[newElementIndex.value] = JSON.parse(JSON.stringify(props.spec.element_default_value))
  elementValidation.value[newElementIndex.value] = []
  frontendOrder.value.push(newElementIndex.value)
  newElementIndex.value += 1
  sendDataUpstream()
  validateList()
}

function updateElementData(newValue: unknown, index: ElementIndex) {
  data.value[index] = newValue
  sendDataUpstream()
}

function sendDataUpstream() {
  backendData.value.splice(0)
  frontendOrder.value.forEach((index: ElementIndex) => {
    backendData.value.push(data.value[index])
  })
}
</script>

<template>
  <table ref="tableRef" class="valuespec_listof vue_list">
    <template v-for="backendIndex in frontendOrder" :key="backendIndex">
      <tr class="listof_element">
        <td class="vlof_buttons">
          <a
            v-if="props.spec.editable_order"
            @dragstart="dragStart"
            @drag="dragging"
            @dragend="dragEnd"
            ><img class="vue element_dragger" />
          </a>
          <a title="Delete this entry">
            <img
              class="icon iconbutton vue icon_close"
              @click.prevent="removeElement(backendIndex)"
            />
          </a>
        </td>
        <td class="vlof_content">
          <FormEdit
            v-model:data="data[backendIndex]"
            :spec="spec.element_template"
            :backend-validation="elementValidation[backendIndex]!"
            @update:data="(new_value: unknown) => updateElementData(new_value, backendIndex)"
          ></FormEdit>
        </td>
      </tr>
    </template>
  </table>
  <a class="vlof_add_button" @click.prevent="addElement">
    <img class="vue icon_plus" />
    <span class="vue add_element_text">{{ spec.add_element_label }}</span>
  </a>
  <FormValidation :validation="validation"></FormValidation>
</template>
