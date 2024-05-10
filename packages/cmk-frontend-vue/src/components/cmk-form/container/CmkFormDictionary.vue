<script setup lang="ts">
import { onMounted, ref, onBeforeMount } from 'vue'
import { extract_value, type ValueAndValidation } from '@/types'
import CmkFormDispatcher from '../CmkFormDispatcher.vue'
import { clicked_checkbox_label } from '@/utils'
import type { VueDictionary, VueDictionaryElement } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: unknown): void
}>()

interface ElementFromProps {
  dict_config: VueDictionaryElement
  is_active: boolean
  data: ValueAndValidation<unknown>
}

const props = defineProps<{
  vueSchema: VueDictionary
  data: ValueAndValidation<Record<string, ValueAndValidation<unknown>>>
}>()

let component_value: { [name: string]: unknown } = {}
const default_values = ref<Record<string, unknown>>({})
const element_components = ref<{ [index: string]: unknown }>({})
const element_active = ref<Record<string, boolean>>({})

onBeforeMount(() => {
  component_value = {}
  console.log('dict schema', props.vueSchema)
  console.log('dict data', props.data)
  const data = extract_value(props.data)
  props.vueSchema.elements.forEach((element: VueDictionaryElement) => {
    const key = element.ident
    default_values.value[key] = element.default_value
    if (key in data) {
      component_value[key] = data[key]
    } else if (element.required) {
      component_value[key] = element.default_value
    } else {
      component_value[key] = undefined
    }
  })
})

onMounted(() => {
  emit('update-value', component_value)
})

function get_elements_from_props(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  const data = extract_value(props.data)
  props.vueSchema.elements.forEach((element: VueDictionaryElement) => {
    elements.push({
      dict_config: element,
      is_active:
        element.ident in element_active.value
          ? element_active.value[element.ident]
          : element.required,
      data: element.ident in data ? data[element.ident] : [default_values.value[element.ident], '']
    })
  })
  return elements
}

function update_key(key: string, new_value: unknown) {
  component_value[key] = new_value
  emit('update-value', component_value)
}

function clicked_dictionary_checkbox_label(event: MouseEvent, key: string) {
  let target = event.target
  if (!target) {
    return
  }

  clicked_checkbox_label(target as HTMLLabelElement)

  const dict_values = extract_value(props.data)
  if (key in dict_values) {
    component_value[key] = undefined
  } else {
    component_value[key] = dict_values[key]
  }
  emit('update-value', component_value)
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
              v-model="element_active[dict_element.dict_config.ident]"
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
              v-if="dict_element.is_active"
              :ref="
                (el) => {
                  element_components[dict_element.dict_config.ident] = el
                }
              "
              :vue-schema="dict_element.dict_config.vue_schema"
              :data="dict_element.data"
              @update-value="(new_value) => update_key(dict_element.dict_config.ident, new_value)"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
