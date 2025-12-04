<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'
import iconUrl from '~cmk-frontend/themes/facelift/images/checkmk_logo.svg'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { AuthMode } from '../twoFactorAuth'

const props = defineProps<{
  currentMode: AuthMode
}>()

const { _t } = usei18n()
const icon = iconUrl

const descriptionText = computed(() => {
  switch (props.currentMode) {
    case 'multipleEnabled':
      return _t(
        'You have multiple methods enabled. Please select the security method you want to use to log in.'
      )
    case 'totp_credentials':
      return _t('Enter the six-digit code from your authenticator app to log in.')
    case 'backup_codes':
      return _t('Use one of your backup codes to sign in.')
    case 'webauthn_credentials':
    default:
      return _t("Please follow your browser's instructions for authentication.")
  }
})
</script>

<template>
  <div class="two-factor-auth-header">
    <a href="https://checkmk.com/">
      <img :src="icon" width="150" />
    </a>
    <CmkHeading type="h1">{{ _t('Two-factor authentication') }}</CmkHeading>
    <div class="two-factor-auth-header__description">
      <CmkParagraph>
        {{ descriptionText }}
      </CmkParagraph>
    </div>
  </div>
</template>

<style scoped>
.two-factor-auth-header {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  text-align: left;
}

.two-factor-auth-header__logo {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding-bottom: var(--dimension-10);
}

.two-factor-auth-header__logo-text {
  font-size: var(--dimension-8);
  font-weight: 500;
  color: var(--success);
  letter-spacing: -0.5px;
}

.two-factor-auth-header__description {
  padding-top: var(--dimension-5);
}
</style>
