<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'
import CmkFormDispatcher from '../CmkFormDispatcher.vue'
import { type ValidationMessages } from '@/utils'
import type { Dictionary, DictionaryElement } from '@/vue_formspec_components'
import type { IComponent } from '@/types'

interface ElementFromProps {
  dict_config: DictionaryElement
  is_active: boolean
}
const props = defineProps<{
  spec: Dictionary
}>()

const data = defineModel('data', { type: Object, required: true })
const default_values: Record<string, unknown> = {}

onBeforeMount(() => {
  props.spec.elements.forEach((element: DictionaryElement) => {
    const key = element.ident
    default_values[key] = element.default_value
  })
  if (props.spec.additional_static_elements) {
    for (const [key, value] of Object.entries(props.spec.additional_static_elements)) {
      data.value[key] = value
    }
  }
})

function setValidation(validation: ValidationMessages) {
  const child_messages: Record<string, ValidationMessages> = {}
  validation.forEach((msg) => {
    if (msg.location.length === 0) {
      return
    }
    const msg_element_ident = msg.location[0]!
    const element_messages = child_messages[msg_element_ident] || []
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    child_messages[msg_element_ident] = element_messages
  })

  props.spec.elements.forEach((element: DictionaryElement) => {
    const ident = element.ident
    if (!(ident in data.value) && !element.required) {
      return
    }
    const element_component = element_components.value[ident]
    if (element_component) {
      element_component.setValidation(child_messages[ident] || [])
    }
  })
}

defineExpose({
  setValidation
})

// TODO: computed
function get_elements_from_props(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  props.spec.elements.forEach((element: DictionaryElement) => {
    elements.push({
      dict_config: element,
      is_active: element.ident in data.value ? true : element.required
    })
  })
  return elements
}

function toggle_element(event: MouseEvent, key: string) {
  let target = event.target
  if (!target) {
    return
  }
  if (key in data.value) {
    delete data.value[key]
  } else {
    data.value[key] = default_values[key]
  }
}
const element_components = ref<Record<string, IComponent>>({})
</script>

<template>
  <table class="dictionary">
    <tbody>
      <tr v-for="dict_element in get_elements_from_props()" :key="dict_element.dict_config.ident">
        <td class="dictleft">
          <span class="checkbox">
            <input
              v-if="!dict_element.dict_config.required"
              :id="$componentId + dict_element.dict_config.ident"
              v-model="dict_element.is_active"
              :onclick="
                (event: MouseEvent) => toggle_element(event, dict_element.dict_config.ident)
              "
              type="checkbox"
            />
            <label :for="$componentId + dict_element.dict_config.ident">
              {{ dict_element.dict_config.parameter_form.title }}
            </label>
          </span>
          <br />
          <div class="dictelement indent">
            <CmkFormDispatcher
              v-if="dict_element.is_active"
              :ref="
                (el) => {
                  element_components[dict_element.dict_config.ident] = el as unknown as IComponent
                }
              "
              v-model:data="data[dict_element.dict_config.ident]"
              :spec="dict_element.dict_config.parameter_form"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
