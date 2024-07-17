<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { List } from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'
import type { IComponent } from '@/types'

const props = defineProps<{
  spec: List
}>()

const data = defineModel<unknown[]>('data', { required: true })
const local_validation = ref<ValidationMessages | null>(null)

type DataWithID = {
  value: unknown
  key: string
}

const data_with_id = ref<DataWithID[]>([])

onMounted(() => {
  data.value.forEach((element) => {
    data_with_id.value.push({
      value: element,
      key: crypto.randomUUID()
    })
  })
})

const validation = ref<ValidationMessages>([])

function setValidation(new_validation: ValidationMessages) {
  const all_element_messages: Record<number, ValidationMessages> = {}
  new_validation.forEach((msg) => {
    if (msg.location.length === 0) {
      return
    }
    const element_index = parseInt(msg.location[0]!)
    const element_messages = all_element_messages[element_index] || []
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    all_element_messages[element_index] = element_messages
  })

  data_with_id.value.forEach((element, index) => {
    const element_messages = all_element_messages[index] || []
    const element_component = list_elements.value[element.key]
    if (element_component) {
      element_component.setValidation(element_messages)
    }
  })
}

defineExpose({
  setValidation
})

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

const list_elements = ref<Record<string, IComponent>>({})
</script>

<template>
  <table ref="table_ref" class="valuespec_listof">
    <template v-for="(element, index) in data_with_id" :key="element.key">
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
              @click.prevent="removeElement(index)"
            />
          </a>
        </td>
        <td class="vlof_content">
          <CmkFormDispatcher
            :ref="
              (el) => {
                list_elements[element.key] = el as unknown as IComponent
              }
            "
            v-model:data="element.value"
            :spec="spec.element_template"
            @update:data="(new_value) => updateElementData(new_value, element.key)"
          ></CmkFormDispatcher>
        </td>
      </tr>
    </template>
  </table>
  <input type="button" class="button" :value="spec.add_element_label" @click.prevent="addElement" />
  <FormValidation :validation="validation"></FormValidation>
</template>
