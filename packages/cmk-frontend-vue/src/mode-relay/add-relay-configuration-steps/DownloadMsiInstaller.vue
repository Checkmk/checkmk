<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & { domain: string; siteName: string; serverPort?: number | null }
>()

const hostWithPort = computed(() =>
  props.serverPort ? `${props.domain}:${props.serverPort}` : props.domain
)

const msiUrl = computed(
  () =>
    `${window.location.protocol}//${hostWithPort.value}/${props.siteName}/check_mk/relays/CheckmkRelayInstaller.msi`
)

const insecureProtocolWarning = computed(() => {
  if (window.location.protocol !== 'https:') {
    return _t(
      'Insecure connection detected (HTTP). For better security, we recommend switching this Checkmk site to HTTPS.'
    )
  } else {
    return false
  }
})

// TODO: Verify this command is correct once the actual MSI installer is ready.
const downloadCommand = computed(
  () => `Invoke-WebRequest -Uri "${msiUrl.value}" -OutFile "CheckmkRelayInstaller.msi"`
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">{{ _t('Download the MSI installer') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'Run the PowerShell command below on the Windows machine on which the Relay will be running ' +
              'to download the MSI installer.'
          )
        }}
      </CmkParagraph>
      <CmkAlertBox v-if="insecureProtocolWarning">{{ insecureProtocolWarning }}</CmkAlertBox>
      <CmkCode
        :code-text="downloadCommand"
        :aria-label="_t('Download relay MSI installer command')"
      ></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
