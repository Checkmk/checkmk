<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch, toRaw } from 'vue'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import HelpText from '@/components/HelpText.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import type {
  CascadingSingleChoice,
  CascadingSingleChoiceElement,
  FormSpec
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useFormEditDispatcher } from '@/form/private'
import { useId } from '@/form/utils'
import { immediateWatch } from '@/lib/watch'
import FormLabel from '@/form/private/FormLabel.vue'
import FormIndent from '@/components/CmkIndent.vue'

const props = defineProps<{
  spec: CascadingSingleChoice
  backendValidation: ValidationMessages
}>()

const FILTER_SHOW_THRESHOLD = 5

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
      } else {
        elementValidation.value.push({
          location: msg.location.slice(1),
          message: msg.message,
          replacement_value: msg.replacement_value
        })
      }
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
        currentValues[key] = structuredClone(toRaw(element.default_value))
      }
    })
  }
)

const selectedOption = computed({
  get(): string {
    return data.value[0] as string
  },
  set(value: string) {
    // Keep old data in case user switches back and they don't loose their modifications
    currentValues[data.value[0]] = data.value[1]

    // Erase backend validation. It does not make sense to keep it when switching between elements.
    elementValidation.value = []

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

const componentId = useId()

const buttonGroupButtons = computed((): Array<{ label: string; value: string }> => {
  return props.spec.elements.map((element: CascadingSingleChoiceElement) => {
    return { label: element.title, value: element.name }
  })
})

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <div
    class="form_cascading_single_choice"
    :class="{ form_cascading_single_choice__horizontal: props.spec.layout === 'horizontal' }"
  >
    <div>
      <FormLabel v-if="$props.spec.label" :for="componentId">
        {{ props.spec.label }}
        <CmkSpace size="small" />
      </FormLabel>
      <template v-if="props.spec.layout === 'button_group'">
        <CmkSpace v-if="$props.spec.label" size="small" :direction="'vertical'" />
        <ToggleButtonGroup
          v-model="selectedOption"
          :options="buttonGroupButtons"
          class="form_cascading_single_choice__button_group"
        />
      </template>
      <template v-else>
        <CmkDropdown
          v-model:selected-option="selectedOption"
          :component-id="componentId"
          :options="spec.elements"
          :no-elements-text="spec.no_elements_text"
          :show-filter="spec.elements.length > FILTER_SHOW_THRESHOLD"
          :required-text="props.spec.i18n_base.required"
          :input-hint="props.spec.input_hint || ''"
          :label="props.spec.label || props.spec.title"
        />
      </template>
      <template v-if="activeElement !== null">
        <CmkSpace size="small" />
        <HelpText :help="activeElement.spec.help" />
      </template>
    </div>
    <CmkSpace v-if="props.spec.layout === 'horizontal'" :size="'medium'" />
    <div>
      <FormIndent :indent="props.spec.layout !== 'horizontal'">
        <template v-if="activeElement !== null">
          <FormEditDispatcher
            :key="data[0]"
            v-model:data="data[1]"
            :spec="activeElement.spec"
            :backend-validation="elementValidation"
          />
        </template>
        <FormValidation :validation="validation"></FormValidation>
      </FormIndent>
    </div>
  </div>
</template>

<style scoped>
.form_cascading_single_choice {
  display: flex;
  flex-direction: column;

  &.form_cascading_single_choice__horizontal {
    flex-direction: row;
  }

  .form_cascading_single_choice__button_group {
    display: inline-block;
  }
}
</style>
