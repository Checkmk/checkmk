<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import { watch, ref } from 'vue'
import { immediateWatch } from '../../../lib/watch'
import HelpText from '@/components/HelpText.vue'
import { useFormEditDispatcher } from '@/form/private'

const props = defineProps<{
  spec: FormSpec.OptionalChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

const embeddedValidation = ref<ValidationMessages>([])
const localValidation = ref<string[]>([])
const checkboxValue = ref<boolean>(data.value !== null)

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    embeddedValidation.value = []
    localValidation.value = []
    newValidation.forEach((msg) => {
      if (msg.location.length === 0) {
        localValidation.value.push(msg.message)
      } else {
        embeddedValidation.value.push({
          location: msg.location.slice(1),
          message: msg.message,
          invalid_value: msg.invalid_value
        })
      }
    })
  }
)

watch(checkboxValue, (newValue: boolean) => {
  if (newValue) {
    data.value = props.spec.parameter_form_default_value
  } else {
    data.value = null
  }
})
// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
</script>

<template>
  <CmkCheckbox v-model="checkboxValue" :label="spec.i18n.label" />
  <HelpText :help="spec.help" />
  <div v-if="data !== null" class="embedded">
    <span v-if="spec.parameter_form.title" class="embedded_title">
      {{ spec.parameter_form.title }}
    </span>
    <FormEditDispatcher
      v-model:data="data"
      :spec="spec.parameter_form"
      :backend-validation="embeddedValidation"
    />
  </div>
  <FormValidation :validation="localValidation"></FormValidation>
</template>

<style scoped>
span.embedded_title {
  margin-right: 3px;
}

div.embedded {
  margin-left: 40px;
}
</style>
