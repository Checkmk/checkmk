<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCode from '@/components/CmkCode.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()

const selectedOs = ref<string>('ubuntu')

const osOptions = [
  { label: 'Ubuntu', value: 'ubuntu' },
  { label: 'Red Hat', value: 'redhat' }
]

const installInstructions = computed(() => {
  if (selectedOs.value === 'ubuntu') {
    return 'sudo apt-get update && sudo apt-get install -y podman'
  } else {
    return 'sudo dnf install -y podman'
  }
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">
        {{ _t('Install Podman') }}
      </CmkHeading>
    </template>

    <template #content>
      <CmkToggleButtonGroup v-model="selectedOs" :options="osOptions" />

      <CmkParagraph>
        {{
          _t(
            'Before deploying the Relay, ensure that Podman is installed on the machine on which the Relay will be running. ' +
              'The Relay is distributed as a container image and requires a functional Podman environment.'
          )
        }}
      </CmkParagraph>

      <CmkCode :code_txt="installInstructions" data-testid="install-podman-command"></CmkCode>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
