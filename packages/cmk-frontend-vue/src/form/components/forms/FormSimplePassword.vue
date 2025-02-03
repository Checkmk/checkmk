<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormValidation from '@/form/components/FormValidation.vue'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import { computed, ref } from 'vue'
import type { SimplePassword } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { immediateWatch } from '@/lib/watch'
import { useId } from '@/form/utils'

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
  <input
    :id="componentId"
    v-model="password"
    :aria-label="props.spec.title"
    type="password"
    :placeholder="'******'"
  />
  <label :for="componentId" />
  <FormValidation :validation="validation"></FormValidation>
</template>
