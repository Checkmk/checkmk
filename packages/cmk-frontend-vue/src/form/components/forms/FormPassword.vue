<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormValidation from '@/form/components/FormValidation.vue'
import type { Password } from '@/form/components/vue_formspec_components'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import { computed, ref } from 'vue'
import { immediateWatch } from '@/form/components/utils/watch'

const props = defineProps<{
  spec: Password
  backendValidation: ValidationMessages
}>()

type PasswordType = 'explicit_password' | 'stored_password'

const data = defineModel<[PasswordType, string, string, boolean]>('data', {
  required: true
})

const validation = ref<Array<string>>([])

const updateValidation = (newValidation: ValidationMessages) => {
  validation.value = newValidation.map((vm) => vm.message)
}

immediateWatch(() => props.backendValidation, updateValidation)

const passwordType = computed({
  get: () => data.value[0] as string,
  set: (value: string) => {
    data.value[0] = value as PasswordType
    data.value[1] = ''
    data.value[2] = ''
    data.value[3] = false
  }
})

const explicitPassword = computed({
  get: () => (data.value[3] ? '' : (data.value[2] as string)!),
  set: (value: string) => {
    validation.value = []
    if (data.value[0] === 'explicit_password') {
      validation.value = validateValue(value, props.spec.validators)
    }
    data.value[1] = ''
    data.value[2] = value
    data.value[3] = false
  }
})

const passwordStoreChoice = computed({
  get: () => data.value[1] as string,
  set: (value: string) => {
    data.value[1] = value
    data.value[2] = ''
    data.value[3] = false
  }
})
</script>

<template>
  <select v-model="passwordType">
    <option value="explicit_password">{{ props.spec.i18n.explicit_password }}</option>
    <option value="stored_password">{{ props.spec.i18n.password_store }}</option>
  </select>
  {{ ' ' }}
  <template v-if="data[0] === 'explicit_password'">
    <input v-model="explicitPassword" type="password" :placeholder="'******'" />
  </template>
  <template v-if="data[0] === 'stored_password'">
    <template v-if="props.spec.password_store_choices.length === 0">
      {{ props.spec.i18n.no_password_store_choices }}
    </template>
    <select v-else v-model="passwordStoreChoice">
      <option
        v-for="{ password_id, name } in props.spec.password_store_choices"
        :key="password_id"
        :value="password_id"
      >
        {{ name }}
      </option>
    </select>
  </template>
  <FormValidation :validation="validation"></FormValidation>
</template>
