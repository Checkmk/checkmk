<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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

// Escape shell arguments by wrapping in single quotes and escaping single quotes.
// This should ensure that regardless of what characters are in the given string argument,
// they will be treated as literal text in the shell command,
// preventing shell injection attacks.
const escapeShellArg = (arg: string): string => {
  return `'${arg.replace(/'/g, "'\"'\"'")}'`
}

const props = defineProps<
  CmkWizardStepProps & {
    relayName: string
    siteName: string
    domain: string
    siteVersion: string
    urlToGetAnAutomationSecret: string
  }
>()

const relayImageReference = computed(() => `checkmk/check-mk-relay:${props.siteVersion}`)

const registrationCommand = computed(() =>
  [
    'sudo docker run --rm \\',
    '  -v checkmk_relay_data:/opt/check-mk-relay/workdir \\',
    `  ${relayImageReference.value} \\`,
    `  sh -c "cmk-relay register \\`,
    `    --server ${props.domain} \\`,
    `    --site ${props.siteName} \\`,
    '    --user agent_registration \\',
    '    --password [automation-secret] \\',
    `    -n ${escapeShellArg(props.relayName)}"`
  ].join('\n')
)

const daemonCommand = computed(() =>
  [
    'sudo docker run --rm \\',
    '  -v checkmk_relay_data:/opt/check-mk-relay/workdir \\',
    `  ${relayImageReference.value} \\`,
    '  sh -c "cmk-relay daemon"'
  ].join('\n')
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">
        {{ _t('Register the relay with your Checkmk site and run it') }}</CmkHeading
      >
    </template>

    <template #content>
      <CmkParagraph>
        {{ _t('Register the Relay to authorize it for communication with your Checkmk site.') }}
      </CmkParagraph>
      <CmkAlertBox variant="info">
        {{ _t(' Go to ') }}
        <a
          :href="props.urlToGetAnAutomationSecret"
          style="text-decoration: underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ _t('this page') }}
        </a>
        {{ _t(' and get an automation secret. Use it in place of [automation-secret]') }}
      </CmkAlertBox>
      <CmkCode :code_txt="registrationCommand"></CmkCode>
      <CmkParagraph>
        {{ _t('After successful registration, start the Relay daemon.') }}
      </CmkParagraph>
      <CmkCode :code_txt="daemonCommand"></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
