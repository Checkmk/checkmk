<script setup lang="ts">
import { onBeforeMount } from 'vue'
import CmkFormDispatcher from '../CmkFormDispatcher.vue'
import { clicked_checkbox_label, type ValidationMessages } from '@/utils'
import type { VueDictionary, VueDictionaryElement } from '@/vue_formspec_components'

interface ElementFromProps {
  dict_config: VueDictionaryElement
  is_active: boolean
}
const props = defineProps<{
  spec: VueDictionary
  validation: ValidationMessages
}>()

const data = defineModel('data', { type: Object, required: true })
const default_values: Record<string, unknown> = {}

onBeforeMount(() => {
  props.spec.elements.forEach((element: VueDictionaryElement) => {
    const key = element.ident
    default_values[key] = element.default_value
  })
})

// TODO: computed
function get_elements_from_props(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  props.spec.elements.forEach((element: VueDictionaryElement) => {
    elements.push({
      dict_config: element,
      is_active: element.ident in data.value ? true : element.required
    })
  })
  return elements
}

function clicked_dictionary_checkbox_label(event: MouseEvent, key: string) {
  let target = event.target
  if (!target) {
    return
  }
  clicked_checkbox_label(target as HTMLLabelElement)
  if (key in data.value) delete data.value[key]
  else data.value[key] = default_values[key]
}

function get_validation_for_child(ident: string): ValidationMessages {
  const child_messages: ValidationMessages = []
  props.validation.forEach((msg) => {
    if (msg.location[0] === ident)
      child_messages.push({
        location: msg.location.slice(1),
        message: msg.message
      })
  })
  return child_messages
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
              v-model="dict_element.is_active"
              type="checkbox"
            />
            <label
              :onclick="
                (event: MouseEvent) =>
                  clicked_dictionary_checkbox_label(event, dict_element.dict_config.ident)
              "
            >
              {{ dict_element.dict_config.vue_schema.title }}
            </label>
          </span>
          <br />
          <div class="dictelement indent">
            <CmkFormDispatcher
              v-if="data[dict_element.dict_config.ident] !== undefined"
              :spec="dict_element.dict_config.vue_schema"
              :validation="get_validation_for_child(dict_element.dict_config.ident)"
              v-model:data="data[dict_element.dict_config.ident]"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
