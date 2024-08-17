<script setup lang="ts">
import { onBeforeMount, ref, watch } from 'vue'
import FormEdit from '../FormEdit.vue'
import type { Dictionary, DictionaryElement } from '@/form/components/vue_formspec_components'
import {
  groupDictionaryValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'

interface ElementFromProps {
  dict_config: DictionaryElement
  is_active: boolean
}
const props = defineProps<{
  spec: Dictionary
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: Object, required: true })
const defaultValues: Record<string, unknown> = {}
const elementValidation = ref<Record<string, ValidationMessages>>({})

onBeforeMount(() => {
  props.spec.elements.forEach((element: DictionaryElement) => {
    const key = element.ident
    defaultValues[key] = element.default_value
  })
  if (props.spec.additional_static_elements) {
    for (const [key, value] of Object.entries(props.spec.additional_static_elements)) {
      data.value[key] = value
    }
  }
  setValidation(props.backendValidation)
})

watch(() => props.backendValidation, setValidation)

function setValidation(newValidation: ValidationMessages) {
  const [, _elementValidation] = groupDictionaryValidations(props.spec.elements, newValidation)
  elementValidation.value = _elementValidation
}

// TODO: computed
function getElementsFromProps(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  props.spec.elements.forEach((element: DictionaryElement) => {
    let isActive = element.ident in data.value ? true : element.required
    if (isActive && data.value[element.ident] === undefined) {
      data.value[element.ident] = JSON.parse(JSON.stringify(defaultValues[element.ident]))
    }
    elements.push({
      dict_config: element,
      is_active: isActive
    })
  })
  return elements
}

function toggleElement(event: MouseEvent, key: string) {
  let target = event.target
  if (!target) {
    return
  }
  if (key in data.value) {
    delete data.value[key]
  } else {
    data.value[key] = defaultValues[key]
  }
}
</script>

<template>
  <table class="dictionary">
    <tbody>
      <tr
        v-for="dict_element in getElementsFromProps()"
        :key="$componentId + dict_element.dict_config.ident"
      >
        <td class="dictleft">
          <span class="checkbox">
            <input
              v-if="!dict_element.dict_config.required"
              :id="$componentId + dict_element.dict_config.ident"
              v-model="dict_element.is_active"
              :onclick="(event: MouseEvent) => toggleElement(event, dict_element.dict_config.ident)"
              type="checkbox"
            />
            <label :for="$componentId + dict_element.dict_config.ident">
              {{ dict_element.dict_config.parameter_form.title }}
            </label>
          </span>
          <br />
          <div class="dictelement indent">
            <FormEdit
              v-if="dict_element.is_active"
              v-model:data="data[dict_element.dict_config.ident]"
              :spec="dict_element.dict_config.parameter_form"
              :backend-validation="elementValidation[dict_element.dict_config.ident]!"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
