<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkWizard from 'cmk-ui-library/components/CmkWizard'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import { createAlert } from '@/mode-alerts/alert-client'
import NameAndServicesStep from '@/mode-alerts/steps/NameAndServicesStep.vue'
import ThresholdsStep from '@/mode-alerts/steps/ThresholdsStep.vue'
import {
  type AlertModel,
  type FolderPaths,
  type HostConditions,
  type PredictionPeriods,
  type ThresholdsValue,
  emptyAlert
} from '@/mode-alerts/types'

const { _t } = usei18n()

const props = defineProps<{
  conditions_form: {
    spec: FormSpec
    data: HostConditions
  }
  thresholds_form: {
    spec: FormSpec
    data: ThresholdsValue
  }
  folder_paths: FolderPaths
  prediction_periods: PredictionPeriods
  activate_changes_url: string
}>()

const currentStep = ref(1)
const model = ref<AlertModel>(emptyAlert(props.conditions_form.data, props.thresholds_form.data))
const saving = ref(false)
const saveError = ref<string | null>(null)

async function saveAlert(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await createAlert(model.value, props.folder_paths, props.prediction_periods)
    if (result.ok) {
      window.location.href = props.activate_changes_url
    } else {
      saveError.value = result.error
    }
  } catch {
    saveError.value = _t('Failed to create the alert.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mode-alerts-alert-wizard-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <NameAndServicesStep
        v-model="model"
        :conditions-spec="conditions_form.spec"
        :folder-paths="folder_paths"
        :index="1"
        :is-completed="() => currentStep > 1"
      />

      <ThresholdsStep
        v-model="model"
        :thresholds-spec="thresholds_form.spec"
        :saving="saving"
        :save-error="saveError"
        :index="2"
        :is-completed="() => false"
        @create="saveAlert"
      />
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
