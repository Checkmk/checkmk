<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, watch } from 'vue'

import usei18n from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import type { AuthConfig } from './otelTypes'
import { isValidPasswordIdForEnvVar } from './validation.ts'

const { _t } = usei18n()

const authMethodId = useId()
const usernameId = useId()
const passwordId = useId()

const props = defineProps<{
  noAuthAllowed: boolean
  availablePasswords: Suggestion[]
  showErrors: boolean
  mayCreatePassword: boolean
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
  if (auth.value.credential === null) {
    return []
  }
  if (auth.value.credential.password) {
    // The env-var rule is about the format of the ID the user just selected,
    // so flag it immediately rather than waiting for the next-step submit.
    if (!isValidPasswordIdForEnvVar(auth.value.credential.password)) {
      return [
        _t("The password ID '%{passwordId}' is not usable by the OTel Collector.", {
          passwordId: auth.value.credential.password
        }),
        _t(
          'It must start with a letter or underscore and ' +
            'contain only letters, digits and underscores.'
        ),
        _t('Please select a different password or create a new one with a valid ID.')
      ]
    }
    return []
  }
  if (props.showErrors) {
    return [_t('Password is required but not specified.')]
  }
  return []
})
</script>

<template>
  <CmkLabel :for="authMethodId">{{ _t('Authentication method') }}</CmkLabel>
  <CmkDropdown
    v-model="auth.method"
    :component-id="authMethodId"
    :options="{ type: 'fixed', suggestions: authMethodOptions }"
    :label="_t('Authentication method')"
  />

  <template v-if="auth.method === 'basicauth' && auth.credential !== null">
    <span />
    <div class="mode-otel-collector-auth-config__sub-field">
      <CmkLabel :for="usernameId">{{ _t('Username') }} <CmkLabelRequired /></CmkLabel>
      <CmkInput
        :id="usernameId"
        v-model="auth.credential.username"
        type="text"
        field-size="medium"
        :placeholder="_t('Username')"
        :external-errors="usernameErrors"
      />

      <CmkLabel :for="passwordId">{{ _t('Password') }} <CmkLabelRequired /></CmkLabel>
      <div class="mode-otel-collector-auth-config__password-row">
        <CmkDropdown
          :key="availablePasswords.length"
          v-model="auth.credential.password"
          :component-id="passwordId"
          :options="{ type: 'fixed', suggestions: availablePasswords }"
          :input-hint="_t('Select password')"
          :label="_t('Password')"
          :form-validation="passwordErrors.length > 0"
          :no-elements-text="_t('No passwords available')"
        />
        <CmkInlineButton :disabled="!mayCreatePassword" @click="emit('createPassword')">{{
          _t('Create')
        }}</CmkInlineButton>
        <CmkHelpText
          v-if="!mayCreatePassword"
          :aria-label="_t('Why is creating a password unavailable?')"
          :help="
            _t(
              'Creating a new password is not available for your account. ' +
                'All of the following are required:' +
                '<ul>' +
                '<li>The permission \'Make changes, perform actions\'.</li>' +
                '<li>The permission \'Password management\'.</li>' +
                '<li>Either the permission \'Write access to all passwords\', ' +
                'or membership in a contact group that could own the new password.</li>' +
                '</ul>'
            )
          "
        />
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
