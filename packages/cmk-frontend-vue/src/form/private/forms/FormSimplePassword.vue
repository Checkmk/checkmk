<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SimplePassword } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import useId from '@/lib/useId'
import { immediateWatch } from '@/lib/watch'

import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import { type ValidationMessages, validateValue } from '@/form/private/validation'

const props = defineProps<{
  spec: SimplePassword
  backendValidation: ValidationMessages
}>()

const data = defineModel<[string, boolean]>('data', { required: true })

const validation = ref<Array<string>>([])

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    validation.value = newValidation.map((vm) => vm.message)
  }
)
const password = computed({
  get: () => (data.value[1] ? '' : data.value[0]),
  set: (value: string) => {
    validation.value = validateValue(value, props.spec.validators)
    data.value[0] = value
    data.value[1] = false
  }
})

const componentId = useId()
</script>

<template>
  <FormValidation :validation="validation"></FormValidation>
  <input
    :id="componentId"
    v-model="password"
    :aria-label="props.spec.title"
    type="password"
    :placeholder="'******'"
    :class="{ 'form-simple-password__validation-error': validation.length > 0 }"
  />
  <label :for="componentId" />
</template>

<style scoped>
.form-simple-password__validation-error {
  border: 1px solid var(--inline-error-border-color);
}
</style>
