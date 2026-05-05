<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import GenerateToken from '@/mode-host/agent-connection-test/components/GenerateToken.vue'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & {
    relayAlias: string
    siteName: string
    domain: string
    agentReceiverPort: number
    siteVersion: string
  }
>()

const ott = ref<string | null | Error>(null)
const hasValidToken = async () => ott.value !== null && !(ott.value instanceof Error)

// TODO: Verify this command is correct once the actual MSI installer is ready.
const installCommand = computed(() => {
  const token = ott.value instanceof Error ? '' : (ott.value ?? '')
  return [
    `msiexec /i checkmk-relay.msi ^`,
    `  RELAY_NAME="${props.relayAlias}" ^`,
    `  INITIAL_TAG_VERSION=${props.siteVersion} ^`,
    `  TARGET_SERVER=${props.domain}:${props.agentReceiverPort} ^`,
    `  TARGET_SITE_NAME=${props.siteName} ^`,
    `  TOKEN=${token}`
  ].join('\n')
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">{{ _t('Run the MSI installer') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'On the Windows machine on which the Relay will be running, run the command below in an ' +
              'elevated Command Prompt to install and register the Relay.'
          )
        }}
      </CmkParagraph>
      <CmkAlertBox variant="info">
        {{ _t('Note that the installation requires administrator privileges.') }}
      </CmkAlertBox>

      <GenerateToken
        v-model="ott"
        token-generation-endpoint-uri="domain-types/relay_registration_token/collections/all"
        :expires-in-seconds="3600"
        :show-validity-text="true"
        :token-generation-body="{}"
        :description="_t('This requires the generation of a registration token.')"
      />

      <CmkCode
        v-if="ott && !(ott instanceof Error)"
        :code-text="installCommand"
        data-testid="run-msi-installer-command"
      ></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="hasValidToken" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
