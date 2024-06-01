<script setup lang="ts">
import { computed, onBeforeMount, onUpdated, type PropType, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type {
  VueCascadingSingleChoice,
  VueCascadingSingleChoiceElement,
  VueSchema
} from '@/vue_formspec_components'

const props = defineProps<{
  spec: VueCascadingSingleChoice
  validation: ValidationMessages
}>()

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
  props.spec.elements.forEach((element: VueCascadingSingleChoiceElement) => {
    const key = element.name
    current_values[key] = element.default_value
    if (data.value[0] === key) {
      data.value[1] = element.default_value
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
      local_validation.value = [{ message: error, location: [''] }]
    })
    emit('update:data', new_value)
  }
})

const validation = computed(() => {
  // If the local validation was never used (null), return the props.validation (backend validation)
  if (local_validation.value === null) {
    return props.validation
  }
  return local_validation.value
})

interface ActiveElement {
  spec: VueSchema
  validation: ValidationMessages
}

const active_element = computed((): ActiveElement => {
  const element = props.spec.elements.find(
    (element: VueCascadingSingleChoiceElement) => element.name === data.value[0]
  )
  return {
    spec: element!.parameter_form,
    validation: []
  }
})

function get_validation_for_child(ident: string): ValidationMessages {
  const child_messages: ValidationMessages = []
  props.validation.forEach((msg) => {
    if (msg.location[0] === ident) {
      child_messages.push({
        location: msg.location.slice(1),
        message: msg.message
      })
    }
  })
  return child_messages
}
</script>

<template>
  <div>
    <select v-model="value">
      <option v-for="element in spec.elements" :key="element.name" :value="element.name">
        {{ element.title }}
      </option>
    </select>
  </div>
  <CmkFormDispatcher
    v-model:data="data[1]"
    :spec="active_element.spec"
    :validation="get_validation_for_child(value[0])"
  ></CmkFormDispatcher>
</template>
