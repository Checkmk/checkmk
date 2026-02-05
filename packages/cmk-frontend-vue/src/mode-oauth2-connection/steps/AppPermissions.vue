<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Add app permissions') }}</CmkHeading>
    </template>

    <template #content>
      {{ _t('Navigate to API permissions and add the following Microsoft Graph permissions.') }}
      <ul>
        <li>{{ 'Mail.Read' }}</li>
        <li>{{ 'Mail.Send' }}</li>
        <li>{{ 'offline_access' }}</li>
      </ul>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
