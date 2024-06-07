<script setup lang="ts">
import { computed, onMounted, onUpdated, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { List } from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'
import type { D3DragEvent } from 'd3'
import { select, selectAll, pointer } from 'd3-selection'
import { drag } from 'd3-drag'

const props = defineProps<{
  spec: List
  validation: ValidationMessages
}>()

const data = defineModel<unknown[]>('data', { required: true })
const local_validation = ref<ValidationMessages | null>(null)

const emit = defineEmits<{
  (e: 'update:data', value: unknown[]): void
}>()

onMounted(() => {
  setup_drag_handler()
})

onUpdated(() => {
  setup_drag_handler()
})

const value = computed(() => {
  return data.value
})

const validation = computed(() => {
  // If the local validation was never used (null), return the props.validation (backend validation)
  if (local_validation.value === null) {
    return props.validation
  }
  return local_validation.value
})

function get_validation_for_child(index: number): ValidationMessages {
  const child_messages: ValidationMessages = []
  props.validation.forEach((msg) => {
    if (msg.location[0] === index.toString()) {
      child_messages.push({
        location: msg.location.slice(1),
        message: msg.message
      })
    }
  })
  return child_messages
}

let table_ref = ref<HTMLTableElement | null>(null)
const class_listof_element = 'listof_element'
const class_element_dragger = 'element_dragger'
const class_vlof_buttons = 'vlof_buttons'

let dragged_index: number = -1
let target_index: number = -1
let dragged_row: HTMLTableRowElement | null = null

function get_dragged_row(event: D3DragEvent<HTMLImageElement, unknown, HTMLImageElement>) {
  if (!event.sourceEvent.target) {
    return
  }
  const target = event.sourceEvent.target
  return target.closest('tr')
}

function drag_start(event: D3DragEvent<HTMLImageElement, unknown, HTMLImageElement>) {
  dragged_row = get_dragged_row(event) as HTMLTableRowElement
  dragged_index = [...table_ref.value!.children].indexOf(dragged_row)
  target_index = -1
  select(dragged_row).classed('dragging', true)
}

function dragging(event: MouseEvent) {
  if (dragged_row == null) {
    return
  }
  if (table_ref.value == null) {
    return
  }
  const y_coords = pointer(event)[1]

  function sibling_middle_point(sibling: Element) {
    let sibling_rect = sibling.getBoundingClientRect()
    return sibling_rect.top + sibling_rect.height / 2
  }

  let previous = dragged_row.previousElementSibling
  while (previous && y_coords < sibling_middle_point(previous)) {
    target_index = [...table_ref.value!.children].indexOf(previous)
    table_ref.value.insertBefore(dragged_row, previous)
    previous = dragged_row.previousElementSibling
  }

  let next = dragged_row.nextElementSibling
  while (next && y_coords > sibling_middle_point(next)) {
    target_index = [...table_ref.value!.children].indexOf(next)
    table_ref.value.insertBefore(dragged_row, next.nextElementSibling)
    next = dragged_row.nextElementSibling
  }
}

function drag_end() {
  selectAll('tr.listof_element').classed('dragging', false)
  if (target_index === -1 || target_index === dragged_index) {
    return
  }
  const new_value = JSON.parse(JSON.stringify(data.value))
  const moved_entry = new_value.splice(dragged_index, 1)[0]
  new_value.splice(target_index, 0, moved_entry)
  emit('update:data', new_value)
}

function setup_drag_handler() {
  const drag_handler = drag<HTMLImageElement, null>()
    .on('start.drag', (event) => drag_start(event))
    .on('drag.drag', (event) => dragging(event))
    .on('end.drag', () => drag_end())
  const elements = select(table_ref.value)
    .selectChildren<HTMLTableRowElement, null>('tr')
    .selectChildren<HTMLTableCellElement, null>('td.' + class_vlof_buttons)
    .select<HTMLImageElement>('img.' + class_element_dragger)
  elements.call(drag_handler)
}

function validate_list() {
  validate_value(value, props.spec.validators!).forEach((error) => {
    local_validation.value = [{ message: error, location: [''] }]
  })
}

function remove_element(index: number) {
  data.value.splice(index, 1)
  validate_list()
}

function add_element() {
  data.value.push(props.spec.element_default_value)
  validate_list()
}

const row_with_uuid = computed(() => {
  // This generates new rows on each data update, causes
  const rows = []
  for (let i = 0; i < value.value.length; i++) {
    rows.push({ uuid: crypto.randomUUID(), value: value.value[i] })
  }
  return rows
})
</script>

<template>
  <table ref="table_ref" class="valuespec_listof">
    <tr
      v-for="(element_row, index) in row_with_uuid"
      :key="element_row.uuid"
      :class="class_listof_element"
    >
      <td :class="class_vlof_buttons">
        <a><img src="themes/modern-dark/images/icon_drag.svg" :class="class_element_dragger" /> </a>
        <a title="Delete this entry">
          <img
            class="icon iconbutton"
            src="themes/modern-dark/images/icon_close.svg"
            @click.prevent="remove_element(index)"
          />
        </a>
      </td>
      <td class="vlof_content">
        <CmkFormDispatcher
          v-model:data="value[index]"
          :spec="spec.element_template"
          :validation="get_validation_for_child(index)"
        ></CmkFormDispatcher>
      </td>
    </tr>
  </table>
  <input
    type="button"
    class="button"
    :value="spec.add_element_label"
    @click.prevent="add_element"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
