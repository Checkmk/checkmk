<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TwoFactorAuth as TwoFactorAuthType } from 'cmk-shared-typing/typescript/two_factor_auth'
import { ref } from 'vue'

import TwoFactorAuth from '@/two-factor-auth/TwoFactorAuthApp.vue'

defineProps<{ screenshotMode: boolean }>()

const availableMethods = ref<TwoFactorAuthType>({
  totp_credentials: true,
  webauthn_credentials: true,
  backup_codes: true
})
</script>

<template>
  <TwoFactorAuth :available-methods="availableMethods" />
</template>
