<script setup lang="ts">
import { onBeforeMount, ref, watch } from 'vue'
import CmkFormDispatcher from '../CmkFormDispatcher.vue'
import { type ValidationMessages } from '@/utils'
import type { Dictionary, DictionaryElement } from '@/vue_formspec_components'

interface ElementFromProps {
  dict_config: DictionaryElement
  is_active: boolean
}
const props = defineProps<{
  spec: Dictionary
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: Object, required: true })
const default_values: Record<string, unknown> = {}
const childValidation = ref<Record<string, ValidationMessages>>({})

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
  setValidation(props.backendValidation)
})

watch(() => props.backendValidation, setValidation)

function setValidation(new_validation: ValidationMessages) {
  childValidation.value = props.spec.elements.reduce(
    (elements, el) => {
      elements[el.ident] = []
      return elements
    },
    {} as Record<string, ValidationMessages>
  )
  new_validation.forEach((msg) => {
    if (msg.location.length === 0) {
      return
    }
    const msg_element_ident = msg.location[0]!
    const element_messages = childValidation.value[msg_element_ident]
    if (element_messages === undefined) {
      throw new Error(`Index ${msg_element_ident} not found in dictionary`)
    }
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    childValidation.value[msg_element_ident] = element_messages
  })
}

// TODO: computed
function get_elements_from_props(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  props.spec.elements.forEach((element: DictionaryElement) => {
    let is_active = element.ident in data.value ? true : element.required
    if (is_active && data.value[element.ident] === undefined) {
      data.value[element.ident] = default_values[element.ident]
    }
    elements.push({
      dict_config: element,
      is_active: is_active
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
              v-model:data="data[dict_element.dict_config.ident]"
              :spec="dict_element.dict_config.parameter_form"
              :backend-validation="childValidation[dict_element.dict_config.ident]!"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
