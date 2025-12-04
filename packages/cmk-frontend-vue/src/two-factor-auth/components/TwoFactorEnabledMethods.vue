<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TwoFactorAuth } from 'cmk-shared-typing/typescript/two_factor_auth'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'

import type { AuthMode } from '../twoFactorAuth'

defineProps<{
  enabledMethods: TwoFactorAuth
}>()

defineEmits<{
  (e: 'switch-mode', mode: AuthMode): void
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="two-factor-auth-two-factor-enabled-methods">
    <CmkButton
      v-if="enabledMethods.totp_credentials"
      class="two-factor-auth-two-factor-enabled-methods__button"
      variant="secondary"
      :aria-label="_t('Authenticate using authenticator app')"
      @click="$emit('switch-mode', 'totp_credentials')"
    >
      {{ _t('Use Authenticator app') }}
    </CmkButton>
    <CmkButton
      v-if="enabledMethods.webauthn_credentials"
      class="two-factor-auth-two-factor-enabled-methods__button"
      variant="secondary"
      :aria-label="_t('Authenticate using security token')"
      @click="$emit('switch-mode', 'webauthn_credentials')"
    >
      {{ _t('Use Security token') }}
    </CmkButton>
    <CmkButton
      v-if="enabledMethods.backup_codes"
      class="two-factor-auth-two-factor-enabled-methods__button"
      variant="secondary"
      :aria-label="_t('Authenticate using backup codes')"
      @click="$emit('switch-mode', 'backup_codes')"
    >
      {{ _t('Use Backup Codes') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.two-factor-auth-two-factor-enabled-methods {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  padding-top: var(--dimension-5);
}

.two-factor-auth-two-factor-enabled-methods__button {
  width: 100%;
}
</style>
