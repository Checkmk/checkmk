<script setup lang="ts">
import { ref, watch } from 'vue'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { List } from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'
import { groupListValidations, validateValue, type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: List
  backendValidation: ValidationMessages
}>()

const backendData = defineModel<unknown[]>('data', { required: true })

type ElementIndex = number
const data = ref<Record<ElementIndex, unknown>>({})
const validation = ref<ValidationMessages>([])
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
  const [_listValidations, _elementValidations] = groupListValidations(
    newBackendValidation,
    backendData.value.length
  )
  validation.value = _listValidations
  elementValidation.value = _elementValidations
}

let tableRef = ref<HTMLTableElement | null>(null)
const CLASS_LISTOF_ELEMENT = 'listof_element'
const CLASS_ELEMENT_DRAGGER = 'element_dragger'
const CLASS_VLOF_BUTTONS = 'vlof_buttons'

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
    validation.value.push({ message: error, location: [], invalid_value: backendData.value })
  })
}

function removeElement(index: ElementIndex) {
  frontendOrder.value.splice(frontendOrder.value.indexOf(index), 1)
  sendDataUpstream()
  validateList()
}

function addElement() {
  data.value[newElementIndex.value] = props.spec.element_default_value
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
  <table ref="tableRef" class="valuespec_listof">
    <template v-for="backendIndex in frontendOrder" :key="backendIndex">
      <tr :class="CLASS_LISTOF_ELEMENT">
        <td :class="CLASS_VLOF_BUTTONS">
          <a
            v-if="props.spec.editable_order"
            @dragstart="dragStart"
            @drag="dragging"
            @dragend="dragEnd"
            ><img src="themes/modern-dark/images/icon_drag.svg" :class="CLASS_ELEMENT_DRAGGER" />
          </a>
          <a title="Delete this entry">
            <img
              class="icon iconbutton"
              src="themes/modern-dark/images/icon_close.svg"
              @click.prevent="removeElement(backendIndex)"
            />
          </a>
        </td>
        <td class="vlof_content">
          <CmkFormDispatcher
            v-model:data="data[backendIndex]"
            :spec="spec.element_template"
            :backend-validation="elementValidation[backendIndex]!"
            @update:data="(new_value: unknown) => updateElementData(new_value, backendIndex)"
          ></CmkFormDispatcher>
        </td>
      </tr>
    </template>
  </table>
  <input type="button" class="button" :value="spec.add_element_label" @click.prevent="addElement" />
  <FormValidation :validation="validation"></FormValidation>
</template>
