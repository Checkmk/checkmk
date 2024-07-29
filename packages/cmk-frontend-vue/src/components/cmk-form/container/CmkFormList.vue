<script setup lang="ts">
import { ref, watch } from 'vue'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { List } from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'
import { group_list_validations, validate_value, type ValidationMessages } from '@/lib/validation'

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
  const [list_validations, element_validations] = group_list_validations(
    newBackendValidation,
    backendData.value.length
  )
  validation.value = list_validations
  elementValidation.value = element_validations
}

let table_ref = ref<HTMLTableElement | null>(null)
const class_listof_element = 'listof_element'
const class_element_dragger = 'element_dragger'
const class_vlof_buttons = 'vlof_buttons'

function dragStart(event: DragEvent) {
  ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.add('dragging')
}

function dragEnd(event: DragEvent) {
  ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.remove('dragging')
}

function dragging(event: DragEvent) {
  if (table_ref.value == null || event.clientY == 0) {
    return
  }
  const table_children = [...table_ref.value!.children]
  const dragged_row = (event.target! as HTMLImageElement).closest('tr')!
  const dragged_index = table_children.indexOf(dragged_row)

  const y_coords = event.clientY
  function sibling_middle_point(sibling: Element) {
    let sibling_rect = sibling.getBoundingClientRect()
    return sibling_rect.top + sibling_rect.height / 2
  }

  let target_index = -1
  let previous: null | undefined | Element = dragged_row.previousElementSibling
  while (previous && y_coords < sibling_middle_point(previous)) {
    target_index = table_children.indexOf(previous)
    previous = table_ref.value!.children[target_index - 1]
  }

  let next: null | undefined | Element = dragged_row.nextElementSibling
  while (next && y_coords > sibling_middle_point(next)) {
    target_index = table_children.indexOf(next)
    next = table_ref.value!.children[target_index + 1]
  }

  if (dragged_index === target_index || target_index === -1) {
    return
  }
  const moved_entry = frontendOrder.value.splice(dragged_index, 1)[0]!
  frontendOrder.value.splice(target_index, 0, moved_entry)
  sendDataUpstream()
}

function validateList() {
  validation.value.splice(0)
  validate_value(backendData.value, props.spec.validators!).forEach((error) => {
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

function updateElementData(new_value: unknown, index: ElementIndex) {
  data.value[index] = new_value
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
  <table ref="table_ref" class="valuespec_listof">
    <template v-for="backendIndex in frontendOrder" :key="backendIndex">
      <tr :class="class_listof_element">
        <td :class="class_vlof_buttons">
          <a
            v-if="props.spec.editable_order"
            @dragstart="dragStart"
            @drag="dragging"
            @dragend="dragEnd"
            ><img src="themes/modern-dark/images/icon_drag.svg" :class="class_element_dragger" />
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
