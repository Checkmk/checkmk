<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CustomServicesWizard } from 'cmk-shared-typing/typescript/mode_custom_services'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref, watch } from 'vue'

import { loadCustomServiceDefinition } from './api'
import { serviceModelFrom } from './definition'
import { type SaveResult, createCustomService, updateCustomService } from './save'
import AssignHostStep from './steps/AssignHostStep.vue'
import DefineMetricStep from './steps/DefineMetricStep.vue'
import { type ServiceModel, emptyService, isMetricSelected, isReadyToCreate } from './types'

const props = defineProps<CustomServicesWizard>()

const { _t } = usei18n()

const currentStep = ref(1)
const model = ref<ServiceModel>(emptyService())
const saving = ref(false)
const saveError = ref<string | null>(null)
const editETag = ref<string | null>(null)
const loading = ref(props.configuration_name !== null)
const loadError = ref<string | null>(null)

// A metric must be selected before the host-assignment step can be reached.
const step1Valid = computed(() => isMetricSelected(model.value))
// A service name and a target host are both required before the service can be created.
const step2Valid = computed(() => isReadyToCreate(model.value))

// Default the service name to the selected metric name (editable in step 2). A loaded service
// always brings its own name along, so prefilling never trips this.
watch(
  () => model.value.metricName,
  (metric) => {
    if (metric && model.value.serviceName.trim() === '') {
      model.value.serviceName = metric
    }
  }
)

onMounted(async () => {
  const configurationName = props.configuration_name
  if (configurationName === null) {
    return
  }
  try {
    const result = await loadCustomServiceDefinition(configurationName)
    if (!result.ok) {
      loadError.value = result.error
      return
    }
    model.value = serviceModelFrom(result.extensions)
    editETag.value = result.etag
  } catch {
    loadError.value = _t('Failed to load the custom service.')
  } finally {
    loading.value = false
  }
})

async function validateStep1(): Promise<boolean> {
  return step1Valid.value
}

const editing = computed(() => props.configuration_name !== null)

const finishLabel = computed(() =>
  editing.value ? _t('Save & activate changes') : _t('Create & activate changes')
)

const failureMessage = computed(() =>
  editing.value
    ? _t('Failed to save the custom service.')
    : _t('Failed to create the custom service.')
)

async function persist(): Promise<SaveResult> {
  const configurationName = props.configuration_name
  if (configurationName === null) {
    return await createCustomService(model.value)
  }
  // Only a failed load leaves no ETag, and that hides the wizard. Never write without one: a
  // wildcard would overwrite a concurrent change.
  if (editETag.value === null) {
    return { ok: false }
  }
  return await updateCustomService(configurationName, model.value, editETag.value)
}

// Persist the custom service, then go to the full activate-changes page so the
// user can apply the pending change.
async function saveService(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await persist()
    if (!result.ok) {
      saveError.value = result.error ?? failureMessage.value
      return
    }
    window.location.href = props.activate_changes_url
  } catch {
    saveError.value = failureMessage.value
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mode-custom-services-custom-services-wizard-app">
    <CmkAlert v-if="loadError" variant="error" :text="untranslated(loadError)" />
    <CmkWizard v-else-if="!loading" v-model="currentStep" mode="guided">
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
          <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />
        </template>
        <template #actions>
          <CmkWizardButton
            type="finish"
            :override-label="finishLabel"
            :disabled="!step2Valid || saving"
            @click="saveService"
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
