<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

defineProps<CmkWizardStepProps & { relayName: string }>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Register the relay with your Checkmk site') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{ _t('Register the Relay to authorize it for communication with your Checkmk site.') }}
      </CmkParagraph>
      <CmkCode
        :code_txt="`cmk-relay register -s <SERVER> -i <SITE> -U <USERNAME> -P <PASSWORD> -n ${relayName}`"
      >
      </CmkCode>
      <CmkAlertBox variant="info">
        {{
          _t(
            'This code snippet includes a one-time token. If you plan to use it multiple times in larger environments, you can check '
          )
        }}
        <a
          href="https://docs.checkmk.com/latest/en/not-yet-defined"
          style="text-decoration: underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ _t('this article') }}
        </a>
        {{ _t(' for more details.') }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
