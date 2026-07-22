<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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

defineProps<CmkWizardStepProps>()

const installScript = `wsl --install --web-download --no-distribution; Restart-Computer -Confirm`
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">{{ _t('Install WSL2') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{ _t('The Relay on Windows runs inside WSL2 (Windows Subsystem for Linux 2).') }}
      </CmkParagraph>
      <CmkParagraph>
        {{ _t('Run the command below in an elevated PowerShell to install it.') }}
      </CmkParagraph>
      <CmkAlertBox>
        {{
          _t(
            'For running WSL2 your system needs to have virtualization enabled. ' +
              'If Windows runs on a VM, the VM must support nested virtualization. ' +
              'This is usually disabled by default and must be enabled at the ' +
              'hypervisor/cloud level, not inside Windows.'
          )
        }}
      </CmkAlertBox>
      <CmkCode :code_txt="installScript" data-testid="install-wsl2-command"></CmkCode>
      <CmkAlertBox variant="warning">
        {{ _t('This command will prompt you to restart the computer to finish the installation.') }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
