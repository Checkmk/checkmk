<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import FormValidation from '@/form/components/FormValidation.vue'
import type { Password } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import { computed, ref } from 'vue'
import { immediateWatch } from '@/lib/watch'
import CmkDropdown from '@/components/CmkDropdown.vue'

const { t } = usei18n('form-password')

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
    const passwordType = value as PasswordType
    const defaultStoreChoice = props.spec.password_store_choices[0]?.password_id ?? ''
    data.value[0] = passwordType
    data.value[1] = passwordType === 'stored_password' ? defaultStoreChoice : ''
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

const passwordTypeOptions = computed(() => {
  return [
    {
      name: 'explicit_password',
      title: props.spec.i18n.explicit_password
    },
    {
      name: 'stored_password',
      title: props.spec.i18n.password_store
    }
  ]
})

const passwordStoreOptions = computed(() => {
  // eslint-disable-next-line @typescript-eslint/naming-convention
  return props.spec.password_store_choices.map(({ password_id, name }) => {
    return {
      name: password_id,
      title: name
    }
  })
})
</script>

<template>
  <CmkDropdown
    v-model:selected-option="passwordType"
    :options="{ type: 'fixed', suggestions: passwordTypeOptions }"
    :label="props.spec.i18n.choose_password_type"
  />
  {{ ' ' }}
  <template v-if="data[0] === 'explicit_password'">
    <input
      v-model="explicitPassword"
      :aria-label="t('explicit-input-aria-label', 'explicit password')"
      type="password"
      :placeholder="'******'"
    />
  </template>
  <template v-if="data[0] === 'stored_password'">
    <template v-if="props.spec.password_store_choices.length === 0">
      {{ props.spec.i18n.no_password_store_choices }}
    </template>
    <CmkDropdown
      v-else
      v-model:selected-option="passwordStoreChoice"
      :options="{ type: 'fixed', suggestions: passwordStoreOptions }"
      :required-text="props.spec.i18n_base.required"
      :label="props.spec.i18n.choose_password_from_store"
    />
  </template>
  <FormValidation :validation="validation"></FormValidation>
</template>
