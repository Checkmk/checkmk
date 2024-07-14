<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { List } from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'

const props = defineProps<{
  spec: List
  validation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })
const local_validation = ref<ValidationMessages | null>(null)

type DataWithID = {
  value: unknown
  validation: ValidationMessages
  key: string
}

const data_with_id = ref<DataWithID[]>([])

onMounted(() => {
  data.value.forEach((element, index) => {
    data_with_id.value.push({
      value: element,
      validation: getValidationForChild(index),
      key: crypto.randomUUID()
    })
  })
})

const validation = computed({
  get(): ValidationMessages {
    // If the local validation was never used (null), return the props.validation (backend validation)
    if (local_validation.value === null) {
      return props.validation
    }
    return local_validation.value
  },
  set(value: ValidationMessages) {
    local_validation.value = value
  }
})

function getValidationForChild(index: number): ValidationMessages {
  const child_messages: ValidationMessages = []
  validation.value.forEach((msg) => {
    if (msg.location[0] === index.toString()) {
      child_messages.push({
        location: msg.location.slice(1),
        message: msg.message,
        invalid_value: msg.invalid_value
      })
    }
  })
  return child_messages
}

let table_ref = ref<HTMLTableElement | null>(null)
const class_listof_element = 'listof_element'
const class_element_dragger = 'element_dragger'
const class_vlof_buttons = 'vlof_buttons'

function dragStart(event: DragEvent) {
  ;(event.target! as HTMLTableRowElement).closest('tr')!.classList.add('dragging')
}

function dragEnd(event: DragEvent) {
  ;(event.target! as HTMLTableRowElement).closest('tr')!.classList.remove('dragging')
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
  const moved_entry = data_with_id.value.splice(dragged_index, 1)[0]!
  data_with_id.value.splice(target_index, 0, moved_entry)
  sendDataUpstream()
}

function validateList() {
  validate_value(data.value, props.spec.validators!).forEach((error) => {
    local_validation.value = [{ message: error, location: [], invalid_value: data.value }]
  })
}

function removeElement(index: number) {
  data_with_id.value.splice(index, 1)
  sendDataUpstream()
  validateList()
}

function addElement() {
  data_with_id.value.push({
    value: props.spec.element_default_value,
    validation: [],
    key: crypto.randomUUID()
  })
  sendDataUpstream()
  validateList()
}

function updateElementData(new_value: unknown, key: string) {
  data_with_id.value.forEach((element) => {
    if (element.key === key) {
      element.value = new_value
    }
  })
  sendDataUpstream()
}
function sendDataUpstream() {
  data.value.splice(0)
  data_with_id.value.forEach((element) => {
    data.value.push(element.value)
  })
}
</script>

<template>
  <table ref="table_ref" class="valuespec_listof">
    <template v-for="(element, index) in data_with_id" :key="element.key">
      <tr :class="class_listof_element">
        <td :class="class_vlof_buttons" @dragstart="dragStart" @drag="dragging" @dragend="dragEnd">
          <a
            ><img src="themes/modern-dark/images/icon_drag.svg" :class="class_element_dragger" />
          </a>
          <a title="Delete this entry">
            <img
              class="icon iconbutton"
              src="themes/modern-dark/images/icon_close.svg"
              @click.prevent="removeElement(index)"
            />
          </a>
        </td>
        <td class="vlof_content">
          <CmkFormDispatcher
            v-model:data="element.value"
            :spec="spec.element_template"
            :validation="element.validation"
            @update:data="(new_value) => updateElementData(new_value, element.key)"
          ></CmkFormDispatcher>
        </td>
      </tr>
    </template>
  </table>
  <input type="button" class="button" :value="spec.add_element_label" @click.prevent="addElement" />
  <FormValidation :validation="validation"></FormValidation>
</template>
