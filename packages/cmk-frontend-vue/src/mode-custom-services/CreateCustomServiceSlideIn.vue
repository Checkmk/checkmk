<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { createCustomService } from './save'
import AssignHostStep from './steps/AssignHostStep.vue'
import { type ServiceModel, isReadyToCreate } from './types'

const { open, initial } = defineProps<{
  open: boolean
  /** The metric query and the prefilled service name; the dialog only edits the host assignment. */
  initial: ServiceModel
}>()

const emit = defineEmits<{
  close: []
}>()

const { _t } = usei18n()

const model = ref<ServiceModel>({ ...initial })
const saving = ref(false)
const saveError = ref<string | null>(null)

const canSave = computed(() => isReadyToCreate(model.value))

async function save(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await createCustomService(model.value)
    if (!result.ok) {
      saveError.value = result.error ?? _t('Failed to create the custom service.')
      return
    }
    emit('close')
  } catch {
    saveError.value = _t('Failed to create the custom service.')
  } finally {
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
      <AssignHostStep v-model:service-name="model.serviceName" v-model:host-name="model.hostName" />
      <CmkAlertBox v-if="saveError" variant="error" size="small">{{ saveError }}</CmkAlertBox>
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

.mode-custom-services-create-custom-service-slide-in__actions {
  display: flex;
  gap: var(--dimension-3);
}
</style>
