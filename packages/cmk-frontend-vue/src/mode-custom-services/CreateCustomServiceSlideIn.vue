<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef, watch } from 'vue'

import NewHostCreationStatus from './NewHostCreationStatus.vue'
import { useNewHostFolders } from './newHostFolders'
import {
  type HostCreationStatus,
  type SaveResult,
  createCustomService,
  hostCreationAfter
} from './save'
import { servicesPreviewBlocksSave, useServicesPreview } from './servicesPreview'
import AssignHostStep from './steps/AssignHostStep.vue'
import ConfigureNameStep from './steps/ConfigureNameStep.vue'
import {
  templatePreviewBlocksSave,
  templatePreviewCreatesHosts,
  useHostNameTemplatePreview
} from './templatePreview'
import { type ServiceModel, isReadyToCreate } from './types'

const { open, initial } = defineProps<{
  open: boolean
  /**
   * The metric query and the prefilled service name; the dialog edits the configuration name and
   * the host assignment.
   */
  initial: ServiceModel
}>()

const emit = defineEmits<{
  close: []
}>()

const { _t } = usei18n()

const model = ref<ServiceModel>({ ...initial })
const saving = ref(false)
const saveError = ref<string | null>(null)
const hostCreation = ref<HostCreationStatus | null>(null)
const templateErrors = ref<string[]>([])
const nameStepRef = useTemplateRef<InstanceType<typeof ConfigureNameStep>>('nameStep')

const templatePreview = useHostNameTemplatePreview(() => model.value)
const newHostFolders = useNewHostFolders(() => templatePreview.preview.value)
const servicesPreview = useServicesPreview(() => model.value, null, {
  getNewHostFolders: () => newHostFolders.toSend.value
})

const canSave = computed(
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

async function save(): Promise<void> {
  saveError.value = null
  saving.value = true
  hostCreation.value = null
  const creatingHosts = templatePreviewCreatesHosts(templatePreview.preview.value)
  let result: SaveResult | null = null
  try {
    if (!((await nameStepRef.value?.validate()) ?? false)) {
      return
    }
    hostCreation.value = creatingHosts ? 'creating' : null
    result = await createCustomService(model.value, newHostFolders.toSend.value)
    if (result.templateError !== undefined) {
      templateErrors.value = [result.templateError]
      return
    }
    if (!result.ok) {
      saveError.value = result.error ?? _t('Failed to create the custom service.')
      return
    }
    emit('close')
  } catch {
    saveError.value = _t('Failed to create the custom service.')
  } finally {
    hostCreation.value = hostCreationAfter(creatingHosts, result)
    saving.value = false
  }
}
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    :header="{ title: _t('Create custom service'), closeButton: true }"
    @close="emit('close')"
  >
    <div class="mode-custom-services-create-custom-service-slide-in">
      <div class="mode-custom-services-create-custom-service-slide-in__name">
        <CmkParagraph>{{ _t('Set the custom service configuration name.') }}</CmkParagraph>
        <ConfigureNameStep ref="nameStep" v-model:configuration-name="model.configurationName" />
      </div>
      <AssignHostStep
        v-model:service-name="model.serviceName"
        v-model:host-name="model.hostName"
        v-model:host-name-template="model.hostNameTemplate"
        :metric-name="model.metricName"
        :attribute-filter="model.attributeFilter"
        :consolidation="model.consolidation"
        :aggregator="model.aggregator"
        :append-series-attributes="model.appendSeriesAttributes"
        :template-errors="templateErrors"
        :template-preview="templatePreview.preview.value"
        :services-preview="servicesPreview.preview.value"
        :new-host-folders="newHostFolders.folders.value"
        @choose-folder="newHostFolders.choose"
      />
      <NewHostCreationStatus v-if="hostCreation !== null" :status="hostCreation" />
      <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />
      <div class="mode-custom-services-create-custom-service-slide-in__actions">
        <CmkButton variant="primary" :disabled="!canSave || saving" @click="save">
          {{ _t('Save') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="emit('close')">
          {{ _t('Cancel') }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.mode-custom-services-create-custom-service-slide-in {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.mode-custom-services-create-custom-service-slide-in__name {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.mode-custom-services-create-custom-service-slide-in__actions {
  display: flex;
  gap: var(--dimension-3);
}
</style>
