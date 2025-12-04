<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TwoFactorAuth } from 'cmk-shared-typing/typescript/two_factor_auth'
import { computed, nextTick, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'

import TwoFactorAuthBackupInput from './components/TwoFactorAuthBackupInput.vue'
import TwoFactorAuthHeader from './components/TwoFactorAuthHeader.vue'
import TwoFactorAuthLinks from './components/TwoFactorAuthLinks.vue'
import TwoFactorAuthOtpInput from './components/TwoFactorAuthOtpInput.vue'
import TwoFactorEnabledMethods from './components/TwoFactorEnabledMethods.vue'
import type { AuthMode } from './twoFactorAuth'
import { completeWebAuthnLogin, verifyCode } from './twoFactorAuthService'
import type { WebAuthnMessage } from './webauthn'

const { _t } = usei18n()

type Message = {
  title: string
  lines: string[]
  type: string
}

type Props = {
  availableMethods?: TwoFactorAuth
}

const props = withDefaults(defineProps<Props>(), {
  availableMethods: () => ({
    totp_credentials: false,
    webauthn_credentials: false,
    backup_codes: false
  })
})

const currentMode = ref<AuthMode>('backup_codes')
const originTarget = ref('index.py')
const otpCode = ref('')
const backupCode = ref('')
const isSubmitting = ref(false)
const message = ref<Message | null>(null)

const otpInputRef = ref<InstanceType<typeof TwoFactorAuthOtpInput> | null>(null)
const backupCodeInputRef = ref<InstanceType<typeof TwoFactorAuthBackupInput> | null>(null)

const activeMethods = Object.entries(props.availableMethods)
  .filter(([_, enabled]) => enabled)
  .map(([method]) => method) as AuthMode[]

const shouldShowMultipleOptions = computed(() => activeMethods.length > 1)

const messageVariant = computed(() => (message.value?.type as 'success' | 'error') || 'error')

function initialMode(): AuthMode {
  if (shouldShowMultipleOptions.value) {
    return 'multipleEnabled'
  }
  return activeMethods[0] || 'backup_codes'
}

function isComplete(): boolean {
  if (currentMode.value === 'totp_credentials') {
    return otpCode.value.length === 6
  }
  if (currentMode.value === 'backup_codes') {
    return backupCode.value.length > 0
  }
  return false
}

function isSubmittable(): boolean {
  return (
    currentMode.value !== 'webauthn_credentials' &&
    currentMode.value !== 'multipleEnabled' &&
    isComplete() &&
    !isSubmitting.value
  )
}

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  const urlMode = params.get('_mode')
  const urlTarget = params.get('_origtarget')

  if (urlTarget) {
    originTarget.value = urlTarget
  }
  if (urlMode && ['totp_credentials', 'backup_codes', 'webauthn_credentials'].includes(urlMode)) {
    currentMode.value = urlMode as AuthMode
  } else {
    currentMode.value = initialMode()
  }

  await focusInput()
  if (currentMode.value === 'webauthn_credentials') {
    await initWebAuthn()
  }
})

async function focusInput() {
  await nextTick()
  if (currentMode.value === 'totp_credentials') {
    otpInputRef.value?.focus()
  } else if (currentMode.value === 'backup_codes') {
    backupCodeInputRef.value?.focus()
  }
}

async function initWebAuthn() {
  try {
    isSubmitting.value = true
    message.value = null

    const webAuthnMsg = await completeWebAuthnLogin()
    message.value = {
      title: webAuthnMsg.title,
      lines: webAuthnMsg.lines,
      type: webAuthnMsg.type === 'success' ? 'success' : 'error'
    }
  } catch (error: unknown) {
    const webauthnError = error as WebAuthnMessage | unknown

    if (webauthnError && typeof webauthnError === 'object' && 'title' in webauthnError) {
      message.value = {
        title: (webauthnError as WebAuthnMessage).title,
        lines: (webauthnError as WebAuthnMessage).lines,
        type: 'error'
      }
    } else {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      message.value = {
        title: _t('WebAuthn Error'),
        lines: [errorMsg],
        type: 'error'
      }
    }
  } finally {
    isSubmitting.value = false
  }
}

async function handleSubmit() {
  if (!isSubmittable()) {
    return
  }

  const code = currentMode.value === 'totp_credentials' ? otpCode.value : backupCode.value
  isSubmitting.value = true
  message.value = null

  try {
    const response = await verifyCode(
      code,
      currentMode.value as 'totp_credentials' | 'backup_codes',
      originTarget.value
    )

    if (response.status === 'OK') {
      const redirectUrl = response.redirect || originTarget.value
      window.location.href = redirectUrl
    }
  } catch {
    isSubmitting.value = false
    message.value = buildMessage()
    await clearAndRefocus()
  }
}

function buildMessage(): Message {
  switch (currentMode.value) {
    case 'totp_credentials':
      return {
        title: _t('Incorrect or expired authenticator code'),
        lines: [_t('Use the latest generated code.')],
        type: 'error'
      }
    case 'backup_codes':
      return {
        title: _t('Invalid backup code'),
        lines: [
          _t('Try a different backup code or contact your Checkmk admin to restore your account.')
        ],
        type: 'error'
      }
    default:
      return {
        title: _t('Authentication failed'),
        lines: [_t('Please try again.')],
        type: 'error'
      }
  }
}

async function switchMode(mode: AuthMode) {
  currentMode.value = mode
  message.value = null

  if (mode === 'webauthn_credentials') {
    await initWebAuthn()
  } else {
    await focusInput()
  }
}

async function clearAndRefocus() {
  if (currentMode.value === 'totp_credentials') {
    otpCode.value = ''
    await nextTick()
    otpInputRef.value?.focus()
  } else {
    backupCode.value = ''
    await nextTick()
    backupCodeInputRef.value?.focus()
  }
}
</script>

<template>
  <div class="two-factor-auth-app">
    <TwoFactorAuthHeader :current-mode="currentMode" />

    <TwoFactorEnabledMethods
      v-if="currentMode === 'multipleEnabled'"
      :enabled-methods="props.availableMethods"
      @switch-mode="switchMode"
    />

    <div v-if="currentMode === 'totp_credentials'">
      <TwoFactorAuthOtpInput
        ref="otpInputRef"
        v-model="otpCode"
        :disabled="isSubmitting"
        :error="message !== null"
        @submit="handleSubmit"
      />
    </div>

    <div v-if="currentMode === 'backup_codes'">
      <TwoFactorAuthBackupInput
        ref="backupCodeInputRef"
        v-model="backupCode"
        :disabled="isSubmitting"
        :error="message !== null"
      />
    </div>

    <CmkAlertBox v-if="message" :variant="messageVariant" :heading="message.title">
      <p v-for="(line, index) in message.lines" :key="index">
        {{ line }}
      </p>
    </CmkAlertBox>

    <CmkButton
      v-if="currentMode !== 'webauthn_credentials' && currentMode !== 'multipleEnabled'"
      class="two-factor-auth-app__button"
      variant="success"
      :disabled="!isSubmittable()"
      @click="handleSubmit"
    >
      <span v-if="isSubmitting">{{ _t('Verifying...') }}</span>
      <span v-else>{{ _t('Submit') }}</span>
    </CmkButton>

    <TwoFactorAuthLinks
      v-if="currentMode !== 'multipleEnabled'"
      :current-mode="currentMode"
      :enabled-methods="props.availableMethods"
      @switch-mode="switchMode"
    />
  </div>
</template>

<style scoped>
.two-factor-auth-app {
  position: relative;
  left: -35px;
  margin: -25px auto 10px;
  background-color: var(--ux-theme-3);
  padding: var(--dimension-10);
  border-radius: var(--dimension-5);
  width: 320px;
  display: flex;
  flex-direction: column;
  color: var(--font-color);
}

.two-factor-auth-app__button {
  width: 100%;
}
</style>
