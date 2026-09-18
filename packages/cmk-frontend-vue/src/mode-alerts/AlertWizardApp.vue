<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import NameAndServicesStep from '@/mode-alerts/steps/NameAndServicesStep.vue'
import { type AlertModel, emptyAlert } from '@/mode-alerts/types'

const { _t } = usei18n()

const currentStep = ref(1)
const model = ref<AlertModel>(emptyAlert())
</script>

<template>
  <div class="mode-alerts-alert-wizard-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <NameAndServicesStep v-model="model" :index="1" :is-completed="() => currentStep > 1" />

      <CmkWizardStep :index="2" :is-completed="() => false">
        <template #header>
          <CmkHeading type="h3">{{ _t('Define threshold') }}</CmkHeading>
        </template>
        <template #content>
          <CmkParagraph>
            {{ _t('Defining the threshold and saving the alert will become available here.') }}
          </CmkParagraph>
        </template>
        <template #actions>
          <CmkWizardButton type="finish" :override-label="_t('Create alert')" disabled />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-alerts-alert-wizard-app {
  padding: var(--dimension-6);
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
