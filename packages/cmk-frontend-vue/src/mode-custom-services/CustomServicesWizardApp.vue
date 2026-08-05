<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CustomServicesWizard } from 'cmk-shared-typing/typescript/mode_custom_services'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import DefineMetricStep from './steps/DefineMetricStep.vue'
import { type ServiceModel, emptyService } from './types'

defineProps<CustomServicesWizard>()

const { _t } = usei18n()

const currentStep = ref(1)
const model = ref<ServiceModel>(emptyService())

// A metric must be selected before the host-assignment step can be reached.
const step1Valid = computed(() => model.value.metricName !== null)

async function validateStep1(): Promise<boolean> {
  return step1Valid.value
}
</script>

<template>
  <div class="mode-custom-services-custom-services-wizard-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
        <template #header>
          <CmkHeading type="h3">{{ _t('Define metric') }}</CmkHeading>
        </template>
        <template #content>
          <DefineMetricStep
            v-model:metric-name="model.metricName"
            v-model:metric-types="model.metricTypes"
            v-model:attribute-filter="model.attributeFilter"
            v-model:consolidation="model.consolidation"
          />
        </template>
        <template #actions>
          <CmkWizardButton type="next" :validation-cb="validateStep1" :disabled="!step1Valid" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="2" :is-completed="() => false">
        <template #header>
          <CmkHeading type="h3">{{ _t('Assign to host') }}</CmkHeading>
        </template>
        <template #content>
          <CmkParagraph>{{
            _t('Registering the metric as a service on a host is implemented in a following story.')
          }}</CmkParagraph>
        </template>
        <template #actions>
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-custom-services-custom-services-wizard-app {
  padding: var(--dimension-6);
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.mode-custom-services-custom-services-wizard-app__header {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}
</style>
