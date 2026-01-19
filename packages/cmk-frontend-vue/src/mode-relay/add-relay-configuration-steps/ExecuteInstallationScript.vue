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
    relayAlias: string
    siteName: string
    domain: string
    siteVersion: string
    urlToGetAnAutomationSecret: string
  }
>()

const installCommand = computed(() =>
  [
    'bash install_relay.sh \\',
    `  --relay-name ${escapeShellArg(props.relayAlias)} \\`,
    `  --initial-tag-version ${props.siteVersion} \\`,
    `  --target-server ${props.domain} \\`,
    `  --target-site-name ${props.siteName} \\`,
    '  --user agent_registration \\',
    '  --password [automation-secret]'
  ].join('\n')
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">
        {{ _t('Download and register the Relay with your Checkmk site') }}</CmkHeading
      >
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'The script will automatically download, register, and run the Relay with your Checkmk site.'
          )
        }}
      </CmkParagraph>
      <CmkAlertBox variant="info">
        {{ _t('Before executing the script, visit ') }}
        <a
          :href="props.urlToGetAnAutomationSecret"
          style="text-decoration: underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ _t('this page') }}
        </a>
        {{
          _t(' to get an automation secret and replace [automation-secret] in the command below.')
        }}
      </CmkAlertBox>
      <CmkCode :code_txt="installCommand"></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
