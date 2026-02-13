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
    isCloudEdition: boolean
    userId: string
  }
>()

const installCommand = computed(() => {
  const username = props.isCloudEdition ? 'api_user' : props.userId

  return [
    'bash install_relay.sh \\',
    `  --relay-name ${escapeShellArg(props.relayAlias)} \\`,
    `  --initial-tag-version ${props.siteVersion} \\`,
    `  --target-server ${props.domain} \\`,
    `  --target-site-name ${props.siteName} \\`,
    `  --user ${username}`
  ].join('\n')
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Run the installation script') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'On the machine on which the Relay will be running, run the command below to execute ' +
              'the downloaded installation script with the parameters shown. The script will ' +
              'automatically download and register the Relay to your Checkmk site and run it afterwards.'
          )
        }}
      </CmkParagraph>
      <CmkParagraph v-if="!props.isCloudEdition">
        {{
          _t(
            'If you do not want to run the script as the specified user — or 2FA is active for that user —, ' +
              'change the parameter to another user with sufficient permissions, such an automation user.'
          )
        }}
      </CmkParagraph>
      <CmkAlertBox variant="info">
        {{ _t('You can only execute the following command as rootless.') }}
        <br />
        {{ _t('If you are logged in as root make sure to change the user using ') }}
        <!-- eslint-disable-next-line vue/no-bare-strings-in-template -->
        <code>su -l &lt;user&gt;</code>
      </CmkAlertBox>

      <CmkCode :code_txt="installCommand" data-testid="run-relay-install-script"></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
