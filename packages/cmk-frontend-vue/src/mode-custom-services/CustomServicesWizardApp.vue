<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CustomServicesWizard } from 'cmk-shared-typing/typescript/mode_custom_services'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { createCustomService } from './save'
import AssignHostStep from './steps/AssignHostStep.vue'
import DefineMetricStep from './steps/DefineMetricStep.vue'
import { type ServiceModel, emptyService, isMetricSelected, isReadyToCreate } from './types'

const props = defineProps<CustomServicesWizard>()

const { _t } = usei18n()

const currentStep = ref(1)
const model = ref<ServiceModel>(emptyService())
const saving = ref(false)
const saveError = ref<string | null>(null)

// A metric must be selected before the host-assignment step can be reached.
const step1Valid = computed(() => isMetricSelected(model.value))
// A service name and a target host are both required before the service can be created.
const step2Valid = computed(() => isReadyToCreate(model.value))

// Default the service name to the selected metric name (editable in step 2).
watch(
  () => model.value.metricName,
  (metric) => {
    if (metric && model.value.serviceName.trim() === '') {
      model.value.serviceName = metric
    }
  }
)

async function validateStep1(): Promise<boolean> {
  return step1Valid.value
}

// Persist the custom service, then go to the full activate-changes page so the
// user can apply the pending change.
async function createService(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await createCustomService(model.value)
    if (!result.ok) {
      saveError.value = result.error ?? _t('Failed to create the custom service.')
      return
    }
    window.location.href = props.activate_changes_url
  } catch {
    saveError.value = _t('Failed to create the custom service.')
  } finally {
    saving.value = false
  }
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
            v-model:aggregator="model.aggregator"
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
          <AssignHostStep
            v-model:service-name="model.serviceName"
            v-model:host-name="model.hostName"
          />
          <CmkAlertBox v-if="saveError" variant="error" size="small">{{ saveError }}</CmkAlertBox>
        </template>
        <template #actions>
          <CmkWizardButton
            type="finish"
            :override-label="_t('Create & activate changes')"
            :disabled="!step2Valid || saving"
            @click="createService"
          />
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
</style>
