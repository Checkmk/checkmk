<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import type { AuthConfig } from './ConfigureCollector.vue'

const { _t } = usei18n()

const props = defineProps<{
  noAuthAllowed: boolean
  availablePasswords: Suggestion[]
  showErrors: boolean
}>()

const emit = defineEmits<{ createPassword: [] }>()

const auth = defineModel<AuthConfig>('auth', { required: true })

const authMethodOptions = computed<Suggestion[]>(() => {
  if (!props.noAuthAllowed) {
    return [{ name: 'basicauth', title: _t('Basic authentication') }]
  }
  return [
    { name: 'none', title: _t('No authentication') },
    { name: 'basicauth', title: _t('Basic authentication') }
  ]
})

watch(
  () => auth.value.method,
  (method) => {
    if (method === 'basicauth' && auth.value.credential === null) {
      auth.value.credential = { username: '', password: null }
    }
  },
  { immediate: true }
)

const usernameErrors = computed<string[]>(() => {
  if (!props.showErrors || auth.value.credential === null) {
    return []
  }
  if (!auth.value.credential.username.trim()) {
    return [_t('Username is required but not specified.')]
  }
  return []
})

const passwordErrors = computed<string[]>(() => {
  if (!props.showErrors || auth.value.credential === null) {
    return []
  }
  if (!auth.value.credential.password) {
    return [_t('Password is required but not specified.')]
  }
  return []
})
</script>

<template>
  <CmkLabel>{{ _t('Authentication method') }}</CmkLabel>
  <CmkDropdown
    v-model:selected-option="auth.method"
    :options="{ type: 'fixed', suggestions: authMethodOptions }"
    :label="_t('Authentication method')"
  />

  <template v-if="auth.method === 'basicauth' && auth.credential !== null">
    <span />
    <div class="mode-otel-collector-auth-config__sub-field">
      <CmkLabel>{{ _t('Username') }} <CmkLabelRequired /></CmkLabel>
      <CmkInput
        v-model="auth.credential.username"
        type="text"
        field-size="MEDIUM"
        :placeholder="_t('Username')"
        :external-errors="usernameErrors"
      />

      <CmkLabel>{{ _t('Password') }} <CmkLabelRequired /></CmkLabel>
      <div class="mode-otel-collector-auth-config__password-row">
        <CmkDropdown
          :key="availablePasswords.length"
          v-model:selected-option="auth.credential.password"
          :options="{ type: 'fixed', suggestions: availablePasswords }"
          :input-hint="_t('Select password')"
          :label="_t('Password')"
          :form-validation="passwordErrors.length > 0"
          :no-elements-text="_t('No passwords available')"
        />
        <CmkInlineButton @click="emit('createPassword')">{{ _t('Create') }}</CmkInlineButton>
      </div>
      <CmkInlineValidation v-if="passwordErrors.length" :validation="passwordErrors" />
    </div>
  </template>
</template>

<style scoped>
.mode-otel-collector-auth-config__sub-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing) var(--dimension-6);
  margin-left: var(--spacing);
  border-left: var(--button-form-border-color) 1px solid;
  padding-left: var(--spacing);
}

.mode-otel-collector-auth-config__password-row {
  display: flex;
  gap: var(--spacing);
  align-items: center;
}
</style>
