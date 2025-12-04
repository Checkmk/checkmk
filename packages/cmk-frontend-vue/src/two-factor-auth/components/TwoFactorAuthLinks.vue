<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TwoFactorAuth } from 'cmk-shared-typing/typescript/two_factor_auth'

import usei18n from '@/lib/i18n'

import type { AuthMode } from '../twoFactorAuth'

defineProps<{
  currentMode: AuthMode
  enabledMethods: TwoFactorAuth
}>()

defineEmits<{
  (e: 'switch-mode', mode: AuthMode): void
}>()

const { _t } = usei18n()
</script>

<template>
  <div v-if="currentMode !== 'multipleEnabled'" class="two-factor-auth-links" role="group">
    <a
      v-if="enabledMethods.totp_credentials && currentMode !== 'totp_credentials'"
      href="#"
      :aria-label="_t('Switch to authenticator app')"
      class="two-factor-auth-links__link"
      @click.prevent="$emit('switch-mode', 'totp_credentials')"
      >{{ _t('Use authenticator app') }}</a
    >
    <a
      v-if="enabledMethods.backup_codes && currentMode !== 'backup_codes'"
      href="#"
      :aria-label="_t('Switch to backup codes')"
      class="two-factor-auth-links__link"
      @click.prevent="$emit('switch-mode', 'backup_codes')"
      >{{ _t('Use backup code') }}</a
    >
    <a
      v-if="enabledMethods.webauthn_credentials && currentMode !== 'webauthn_credentials'"
      href="#"
      :aria-label="_t('Switch to security token')"
      class="two-factor-auth-links__link"
      @click.prevent="$emit('switch-mode', 'webauthn_credentials')"
      >{{ _t('Use security token') }}</a
    >
  </div>
</template>

<style scoped>
.two-factor-auth-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-6);
  padding-top: var(--dimension-6);
}

.two-factor-auth-links__link {
  width: 277px;
  color: var(--color-white-100, #fff);
  text-align: center;
  font-size: var(--font-size-normal);
  font-style: normal;
  font-weight: var(--font-weight-bold);
  text-decoration-line: underline;
  text-decoration-skip-ink: none;
}

.two-factor-auth-links__link:hover {
  color: var(--font-color-dimmed);
}
</style>
