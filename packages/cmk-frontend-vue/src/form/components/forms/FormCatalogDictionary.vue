<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DictionaryElement } from '@/form/components/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import { immediateWatch } from '@/form/components/utils/watch'
import {
  groupDictionaryValidations,
  requiresSomeInput,
  type ValidationMessages
} from '@/form/components/utils/validation'
import { ref } from 'vue'
import HelpText from '@/components/HelpText.vue'

const props = defineProps<{
  elements: Array<DictionaryElement>
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, unknown>>({ required: true })

immediateWatch(
  () => props.elements,
  (newValue) => {
    newValue.forEach((element) => {
      if (!(element.ident in data.value)) {
        data.value[element.ident] = element.default_value
      }
    })
  }
)

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, _elementValidation] = groupDictionaryValidations(props.elements, newValidation)
    elementValidation.value = _elementValidation
  }
)

function isRequired(element: DictionaryElement): boolean {
  return requiresSomeInput(element.parameter_form.validators)
}
</script>

<template>
  <tr v-for="element in elements" :key="element.ident">
    <td class="legend">
      <div class="title">
        {{ element.parameter_form.title }}
        <HelpText :help="element.parameter_form.help" />
        <span
          class="dots"
          :class="{
            required: isRequired(element)
          }"
        >
          {{ Array(200).join('.') }}</span
        >
      </div>
    </td>
    <td class="content">
      <FormEdit
        v-model:data="data[element.ident]!"
        :backend-validation="elementValidation[element.ident]!"
        :spec="element.parameter_form"
      />
    </td>
  </tr>
</template>
