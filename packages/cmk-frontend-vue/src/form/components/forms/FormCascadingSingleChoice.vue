<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import type {
  CascadingSingleChoice,
  CascadingSingleChoiceElement,
  FormSpec
} from '@/form/components/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: CascadingSingleChoice
  backendValidation: ValidationMessages
}>()

const validation = ref<Array<string>>([])
const elementValidation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    validation.value = []
    elementValidation.value = []
    newValidation.forEach((msg) => {
      if (msg.location.length === 0) {
        validation.value.push(msg.message)
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

const data = defineModel<[string, unknown]>('data', { required: true })

const currentValues: Record<string, unknown> = {}
immediateWatch(
  () => props.spec.elements,
  (newValue) => {
    newValue.forEach((element: CascadingSingleChoiceElement) => {
      const key = element.name
      if (data.value[0] === key) {
        currentValues[key] = data.value[1]
      } else {
        currentValues[key] = element.default_value
      }
    })
  }
)

const selectedOption = computed({
  get(): string {
    return data.value[0] as string
  },
  set(value: string) {
    // keep old data in case user switches back and they don't loose their modifications
    currentValues[data.value[0]] = data.value[1]

    validation.value = []
    const newValue: [string, unknown] = [value, currentValues[value]]
    validateValue(value, props.spec.validators!).forEach((error) => {
      validation.value = [error]
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
  <div class="choice">
    <select :id="$componentId" v-model="selectedOption">
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
      :key="data[0]"
      v-model:data="data[1]"
      :spec="activeElement.spec"
      :backend-validation="elementValidation"
    ></FormEdit>
    <FormValidation :validation="validation"></FormValidation>
  </template>
</template>

<style scoped>
div.choice {
  margin-bottom: 5px;
  margin-right: 5px;
}
</style>
