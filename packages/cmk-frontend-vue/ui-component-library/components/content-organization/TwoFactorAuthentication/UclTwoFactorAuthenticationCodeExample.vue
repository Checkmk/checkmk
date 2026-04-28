<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TwoFactorAuth as TwoFactorAuthType } from 'cmk-shared-typing/typescript/two_factor_auth'

import TwoFactorAuth from '@/two-factor-auth/TwoFactorAuthApp.vue'

const methods: TwoFactorAuthType = {
  totp_credentials: true,
  webauthn_credentials: true,
  backup_codes: false
}
</script>

<template>
  <TwoFactorAuth :available-methods="methods" />
</template>
