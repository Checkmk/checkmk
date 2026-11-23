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
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref, useTemplateRef, watch } from 'vue'

import NewHostCreationStatus from './NewHostCreationStatus.vue'
import { loadCustomServiceDefinition } from './api'
import { serviceModelFrom } from './definition'
import { useNewHostFolders } from './newHostFolders'
import {
  type HostCreationStatus,
  type SaveResult,
  createCustomService,
  hostCreationAfter,
  updateCustomService
} from './save'
import { servicesPreviewBlocksSave, useServicesPreview } from './servicesPreview'
import AssignHostStep from './steps/AssignHostStep.vue'
import ConfigureNameStep from './steps/ConfigureNameStep.vue'
import DefineMetricStep from './steps/DefineMetricStep.vue'
import {
  templatePreviewBlocksSave,
  templatePreviewCreatesHosts,
  useHostNameTemplatePreview
} from './templatePreview'
import { type ServiceModel, emptyService, isMetricSelected, isReadyToCreate } from './types'

const props = defineProps<CustomServicesWizard>()

const { _t } = usei18n()

const editing = props.configuration_name !== null
// A stored service keeps its name (the update endpoint cannot rename it), so editing skips step 1.
const currentStep = ref(editing ? 2 : 1)
const model = ref<ServiceModel>(emptyService())
const saving = ref(false)
const saveError = ref<string | null>(null)
const hostCreation = ref<HostCreationStatus | null>(null)
const templateErrors = ref<string[]>([])
const editETag = ref<string | null>(null)
const loading = ref(editing)
const loadError = ref<string | null>(null)
const nameStepRef = useTemplateRef<InstanceType<typeof ConfigureNameStep>>('nameStep')

// A metric must be selected before the host-assignment step can be reached.
const metricStepValid = computed(() => isMetricSelected(model.value))
// Only looked up on the host step, so editing the metric step does not query on every change
const templatePreview = useHostNameTemplatePreview(() =>
  currentStep.value === 3 ? model.value : null
)
const newHostFolders = useNewHostFolders(() => templatePreview.preview.value)
const servicesPreview = useServicesPreview(
  () => (currentStep.value === 3 ? model.value : null),
  props.configuration_name,
  { getNewHostFolders: () => newHostFolders.toSend.value }
)
// A service name and a host, or a host name template whose matches allow saving, are required,
// and the names of the services must not clash.
const hostStepValid = computed(
  () =>
    isReadyToCreate(model.value) &&
    !templatePreviewBlocksSave(templatePreview.preview.value) &&
    !servicesPreviewBlocksSave(servicesPreview.preview.value)
)

watch(
  () => model.value.hostNameTemplate,
  () => {
    templateErrors.value = []
  }
)

// Default the service name to the selected metric name (editable in the assign host step). A
// loaded service always brings its own name along, so prefilling never trips this.
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
    model.value = serviceModelFrom(configurationName, result.extensions)
    editETag.value = result.etag
  } catch {
    loadError.value = _t('Failed to load the custom service.')
  } finally {
    loading.value = false
  }
})

async function validateNameStep(): Promise<boolean> {
  return (await nameStepRef.value?.validate()) ?? false
}

async function validateMetricStep(): Promise<boolean> {
  return metricStepValid.value
}

const finishLabel = computed(() =>
  editing ? _t('Save & activate changes') : _t('Create & activate changes')
)

const failureMessage = computed(() =>
  editing ? _t('Failed to save the custom service.') : _t('Failed to create the custom service.')
)

async function persist(): Promise<SaveResult> {
  const configurationName = props.configuration_name
  if (configurationName === null) {
    return await createCustomService(model.value, newHostFolders.toSend.value)
  }
  // Only a failed load leaves no ETag, and that hides the wizard. Never write without one: a
  // wildcard would overwrite a concurrent change.
  if (editETag.value === null) {
    return { ok: false }
  }
  return await updateCustomService(
    configurationName,
    model.value,
    editETag.value,
    newHostFolders.toSend.value
  )
}

// The alert wizard starts from the conditions of the custom service it is told about.
function alertUrlFor(createAlertUrl: string): string {
  const separator = createAlertUrl.includes('?') ? '&' : '?'
  const name = encodeURIComponent(model.value.configurationName)
  return `${createAlertUrl}${separator}custom_service=${name}`
}

// Persist the custom service, then go on to `target`: the full activate-changes page so the
// user can apply the pending change, or the alert wizard, whose end activates it as well.
async function saveService(target: string): Promise<void> {
  saveError.value = null
  saving.value = true
  const creatingHosts = templatePreviewCreatesHosts(templatePreview.preview.value)
  hostCreation.value = creatingHosts ? 'creating' : null
  let result: SaveResult | null = null
  let leaving = false
  try {
    result = await persist()
    if (result.templateError !== undefined) {
      templateErrors.value = [result.templateError]
      return
    }
    if (!result.ok) {
      saveError.value = result.error ?? failureMessage.value
      return
    }
    leaving = true
    window.location.href = target
  } catch {
    saveError.value = failureMessage.value
  } finally {
    hostCreation.value = hostCreationAfter(creatingHosts, result)
    // The buttons stay disabled while the next page loads, so a second click cannot save the
    // service again.
    saving.value = leaving
  }
}
</script>

<template>
  <div class="mode-custom-services-custom-services-wizard-app">
    <CmkAlert v-if="loadError" variant="error" :text="untranslated(loadError)" />
    <CmkWizard v-else-if="!loading" v-model="currentStep" mode="guided">
      <CmkWizardStep v-if="!editing" :index="1" :is-completed="() => currentStep > 1">
        <template #header>
          <CmkHeading type="h3">{{ _t('General configuration properties') }}</CmkHeading>
        </template>
        <template #content>
          <div class="mode-custom-services-custom-services-wizard-app__name-step">
            <CmkParagraph>{{ _t('Set the custom service configuration name.') }}</CmkParagraph>
            <ConfigureNameStep
              ref="nameStep"
              v-model:configuration-name="model.configurationName"
            />
          </div>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :validation-cb="validateNameStep" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
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
            :time-picker="props.time_picker"
          />
        </template>
        <template #actions>
          <CmkWizardButton
            type="next"
            :validation-cb="validateMetricStep"
            :disabled="!metricStepValid"
          />
          <CmkWizardButton v-if="!editing" type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="3" :is-completed="() => false">
        <template #header>
          <CmkHeading type="h3">{{ _t('Assign to host') }}</CmkHeading>
        </template>
        <template #content>
          <!-- Mounted only while shown, so editing the metric step asks the backend nothing -->
          <AssignHostStep
            v-if="currentStep === 3"
            v-model:service-name="model.serviceName"
            v-model:host-name="model.hostName"
            v-model:host-name-template="model.hostNameTemplate"
            :template-errors="templateErrors"
            :template-preview="templatePreview.preview.value"
            :services-preview="servicesPreview.preview.value"
            :new-host-folders="newHostFolders.folders.value"
            :metric-name="model.metricName"
            :attribute-filter="model.attributeFilter"
            :consolidation="model.consolidation"
            :aggregator="model.aggregator"
            :append-series-attributes="model.appendSeriesAttributes"
            @choose-folder="newHostFolders.choose"
          />
          <NewHostCreationStatus v-if="hostCreation !== null" :status="hostCreation" />
          <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />
        </template>
        <template #actions>
          <CmkWizardButton
            type="finish"
            :override-label="finishLabel"
            :disabled="!hostStepValid || saving"
            @click="saveService(props.activate_changes_url)"
          />
          <CmkWizardButton
            v-if="props.create_alert_url !== null"
            type="other"
            :override-label="_t('Create & add alert')"
            icon-name="alerts"
            :disabled="!hostStepValid || saving"
            @click="saveService(alertUrlFor(props.create_alert_url))"
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

.mode-custom-services-custom-services-wizard-app__name-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
