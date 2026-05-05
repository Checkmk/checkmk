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

// TODO: Verify this command is correct once the actual MSI installer is ready.
const installCommand = 'wsl --install'
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">{{ _t('Install WSL2') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'The Relay on Windows runs inside WSL2 (Windows Subsystem for Linux 2). ' +
              'Run the command below in an elevated PowerShell or Command Prompt to install WSL2.'
          )
        }}
      </CmkParagraph>
      <CmkCode :code-text="installCommand" data-testid="install-wsl2-command"></CmkCode>
      <CmkAlertBox variant="info">
        {{ _t('A system reboot may be required after installing WSL2 before proceeding.') }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
