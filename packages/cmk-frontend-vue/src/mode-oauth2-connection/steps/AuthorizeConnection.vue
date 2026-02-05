<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Authorize the connection') }}</CmkHeading>
    </template>

    <template #content>
      {{
        _t(
          'A new tab will be opened and you will need to log in to Microsoft Azure to authorize the application. The process has to be completed within 5 minutes.'
        )
      }}
    </template>

    <template #actions>
      <CmkWizardButton type="next" :override-label="_t('Start authorization')" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
