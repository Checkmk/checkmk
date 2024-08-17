<script setup lang="ts">
import { computed, onBeforeMount, onUpdated, type PropType, ref, watch } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import type {
  CascadingSingleChoice,
  CascadingSingleChoiceElement,
  FormSpec
} from '@/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: CascadingSingleChoice
  backendValidation: ValidationMessages
}>()

const validation = ref<ValidationMessages>([])
const elementValidation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    validation.value = []
    elementValidation.value = []
    newValidation.forEach((msg) => {
      if (msg.location.length === 0) {
        validation.value.push(msg)
        return
      }
      elementValidation.value.push({
        location: msg.location.slice(1),
        message: msg.message,
        invalid_value: msg.invalid_value
      })
    })
  },
  { immediate: true }
)

const data = defineModel('data', {
  type: Object as PropType<[string, unknown]>,
  required: true
})

const currentValues: Record<string, unknown> = {}
onBeforeMount(() => {
  props.spec.elements.forEach((element: CascadingSingleChoiceElement) => {
    const key = element.name
    if (data.value[0] === key) {
      currentValues[key] = data.value[1]
    } else {
      currentValues[key] = element.default_value
    }
  })
})

onUpdated(() => {
  if (data.value[0] in currentValues) {
    currentValues[data.value[0]] = data.value[1]
  }
})

const value = computed({
  get(): string {
    return data.value[0] as string
  },
  set(value: string) {
    validation.value = []
    const newValue: [string, unknown] = [value, currentValues[value]]
    validateValue(value, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [''], invalid_value: value }]
    })
    data.value = newValue
  }
})

interface ActiveElement {
  spec: FormSpec
  validation: ValidationMessages
}

const activeElement = computed((): ActiveElement | null => {
  const element = props.spec.elements.find(
    (element: CascadingSingleChoiceElement) => element.name === data.value[0]
  )
  if (element === undefined) {
    return null
  }
  return {
    spec: element!.parameter_form,
    validation: []
  }
})
</script>

<template>
  <div>
    <select :id="$componentId" v-model="value">
      <option v-if="activeElement == null" disabled selected hidden value="">
        {{ props.spec.input_hint }}
      </option>
      <option v-for="element in spec.elements" :key="element.name" :value="element.name">
        {{ element.title }}
      </option>
    </select>
    <label v-if="$props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  </div>
  <template v-if="activeElement != null">
    <FormEdit
      v-model:data="data[1]"
      :spec="activeElement.spec"
      :backend-validation="elementValidation"
    ></FormEdit>
    <FormValidation :validation="validation"></FormValidation>
  </template>
</template>
