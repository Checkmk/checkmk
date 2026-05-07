<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'
import { type TwoFactorAuth as TwoFactorAuthType } from 'cmk-shared-typing/typescript/two_factor_auth'

import codeExample from './UclTwoFactorAuthenticationCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the different elements.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the previous element in reverse order.'
  },
  {
    keys: ['Enter'],
    description: 'Submits the form when focused within the input fields.'
  }
]

export const panelConfig = {
  totp: { type: 'boolean' as const, title: 'Enable TOTP', initialState: true },
  webauthn: { type: 'boolean' as const, title: 'Enable WebAuthn', initialState: true },
  backup: { type: 'boolean' as const, title: 'Enable Backup Codes', initialState: true }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import TwoFactorAuth from '@/two-factor-auth/TwoFactorAuthApp.vue'

defineProps<{ screenshotMode: boolean }>()

// We're not using PanelStateCreator here as TwoFactorAuth doesn't follow the usual pattern.
const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const dynamicAvailableMethods = computed<TwoFactorAuthType>(() => ({
  totp_credentials: propState.value.totp,
  webauthn_credentials: propState.value.webauthn,
  backup_codes: propState.value.backup
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>TwoFactorAuthApp</UclDetailPageHeader>

    <UclDetailPageComponent>
      <TwoFactorAuth
        :key="JSON.stringify(dynamicAvailableMethods)"
        :available-methods="dynamicAvailableMethods"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
