<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & { domain: string; siteName: string; serverPort?: number | null }
>()

const hostWithPort = computed(() =>
  props.serverPort ? `${props.domain}:${props.serverPort}` : props.domain
)

const installScriptUrl = computed(
  () =>
    `${window.location.protocol}//${hostWithPort.value}/${props.siteName}/check_mk/relays/install_relay.sh`
)

const insecureProtocolWarning = computed(() => {
  if (window.location.protocol !== 'https:') {
    return _t(
      'Insecure connection detected (HTTP). For better security, we recommend switching this Checkmk site to HTTPS. '
    )
  } else {
    return false
  }
})

const downloadCommand = computed(() => `curl -O ${installScriptUrl.value}`)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Download the Relay installation script') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'Run the command below to make the Relay installation script available to the machine on which the Relay will be running.'
          )
        }}
      </CmkParagraph>
      <CmkAlert v-if="insecureProtocolWarning" :text="insecureProtocolWarning" />
      <CmkCode
        :code-text="downloadCommand"
        :aria-label="_t('Download relay install script command')"
      ></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
    </template>
  </CmkWizardStep>
</template>
