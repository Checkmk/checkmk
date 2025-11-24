<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const props = defineProps<CmkWizardStepProps & { siteVersion: string }>()

const relayImageReference = computed(() => `checkmk/check-mk-relay:${props.siteVersion}`)

const codeText = computed(() => `sudo docker pull ${relayImageReference.value}`)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Download the relay to your environment') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{ _t('Download the Relay container image.') }}
      </CmkParagraph>
      <CmkCode :code_txt="codeText"></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
    </template>
  </CmkWizardStep>
</template>
