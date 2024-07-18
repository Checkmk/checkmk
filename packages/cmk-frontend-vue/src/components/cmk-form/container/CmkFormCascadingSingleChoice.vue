<script setup lang="ts">
import { computed, onBeforeMount, onUpdated, type PropType, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type {
  CascadingSingleChoice,
  CascadingSingleChoiceElement,
  FormSpec
} from '@/vue_formspec_components'
import { FormValidation } from '@/components/cmk-form'
import type { IComponent } from '@/types'

const props = defineProps<{
  spec: CascadingSingleChoice
}>()

const validation = ref<ValidationMessages>([])
function setValidation(new_validation: ValidationMessages) {
  if (active_component.value === undefined) {
    throw new Error('active_component is undefined')
  }

  validation.value = []
  const element_messages: ValidationMessages = []
  new_validation.forEach((msg) => {
    if (msg.location.length === 0) {
      validation.value.push(msg)
      return
    }
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
  })
  active_component.value.setValidation(element_messages)
}

defineExpose({
  setValidation
})

const data = defineModel('data', {
  type: Object as PropType<[string, unknown]>,
  required: true
})

const local_validation = ref<ValidationMessages | null>(null)

const emit = defineEmits<{
  (e: 'update:data', value: [string, unknown]): void
}>()

const current_values: Record<string, unknown> = {}
onBeforeMount(() => {
  props.spec.elements.forEach((element: CascadingSingleChoiceElement) => {
    const key = element.name
    if (data.value[0] === key) {
      current_values[key] = data.value[1]
    } else {
      current_values[key] = element.default_value
    }
  })
})

onUpdated(() => {
  if (data.value[0] in current_values) {
    current_values[data.value[0]] = data.value[1]
  }
})

const value = computed({
  get(): string {
    return data.value[0] as string
  },
  set(value: string) {
    local_validation.value = []
    const new_value: [string, unknown] = [value, current_values[value]]
    validate_value(value, props.spec.validators!).forEach((error) => {
      local_validation.value = [{ message: error, location: [''], invalid_value: value }]
    })
    emit('update:data', new_value)
  }
})

interface ActiveElement {
  spec: FormSpec
  validation: ValidationMessages
}

const active_element = computed((): ActiveElement => {
  const element = props.spec.elements.find(
    (element: CascadingSingleChoiceElement) => element.name === data.value[0]
  )
  return {
    spec: element!.parameter_form,
    validation: []
  }
})
const active_component = ref<IComponent>()
</script>

<template>
  <div>
    <select :id="$componentId" v-model="value">
      <option v-for="element in spec.elements" :key="element.name" :value="element.name">
        {{ element.title }}
      </option>
      <label v-if="$props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
    </select>
  </div>
  <CmkFormDispatcher
    ref="active_component"
    v-model:data="data[1]"
    :spec="active_element.spec"
  ></CmkFormDispatcher>
  <FormValidation :validation="validation"></FormValidation>
</template>
