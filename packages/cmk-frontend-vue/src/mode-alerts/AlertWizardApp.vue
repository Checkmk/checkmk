<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkWizard from 'cmk-ui-library/components/CmkWizard'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import { type SaveResult, createAlert, loadAlert, updateAlert } from '@/mode-alerts/alert-client'
import NameStep from '@/mode-alerts/steps/NameStep.vue'
import ServicesStep from '@/mode-alerts/steps/ServicesStep.vue'
import ThresholdsStep from '@/mode-alerts/steps/ThresholdsStep.vue'
import {
  type AlertModel,
  type AlertPrefill,
  type FolderPaths,
  type HostConditions,
  type PredictionPeriods,
  type ThresholdsValue,
  alertModelFrom,
  emptyAlert,
  prefilledAlert
} from '@/mode-alerts/types'

const { _t } = usei18n()

const props = defineProps<{
  configuration_name: string | null
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
  time_picker: GlobalTimePickerProps
  warning_color: string
  critical_color: string
  activate_changes_url: string
  // Set when the alert is added for a custom service, from its definition
  prefill?: AlertPrefill | null
  prefill_error?: string | null
}>()

const editing = props.configuration_name !== null
// A stored alert keeps its name (the update endpoint cannot rename it), so editing skips step 1.
const currentStep = ref(editing ? 2 : 1)
const prefill = props.prefill ?? null
const model = ref<AlertModel>(
  prefill === null
    ? emptyAlert(props.conditions_form.data, props.thresholds_form.data)
    : prefilledAlert(prefill, props.conditions_form.data, props.thresholds_form.data)
)
// The check only holds for the match the backend derived, not for one the user changed it to.
const matchMaySelectOthers = computed(
  () =>
    prefill !== null &&
    !prefill.singles_out &&
    model.value.matchType === prefill.match_type &&
    model.value.servicePattern === prefill.service_pattern
)
const saving = ref(false)
const saveError = ref<string | null>(null)
const editETag = ref<string | null>(null)
const loading = ref(editing)
const loadError = ref<string | null>(null)

onMounted(async () => {
  const configurationName = props.configuration_name
  if (configurationName === null) {
    return
  }
  try {
    const result = await loadAlert(configurationName)
    if (!result.ok) {
      loadError.value = result.error
      return
    }
    try {
      model.value = alertModelFrom(result.extensions, props.folder_paths, props.prediction_periods)
    } catch {
      // The stored alert was read, but the wizard has no choice to show part of it in.
      loadError.value = _t(
        'This alert uses conditions the editor cannot show, for example a folder you cannot access.'
      )
      return
    }
    editETag.value = result.etag
  } catch {
    loadError.value = _t('Failed to load the alert.')
  } finally {
    loading.value = false
  }
})

const finishLabel = computed(() =>
  editing ? _t('Save & activate changes') : _t('Create & activate changes')
)

const failureMessage = computed(() =>
  editing ? _t('Failed to save the alert.') : _t('Failed to create the alert.')
)

async function persist(): Promise<SaveResult> {
  const configurationName = props.configuration_name
  if (configurationName === null) {
    return await createAlert(model.value, props.folder_paths, props.prediction_periods)
  }
  // Only a failed load leaves no ETag, and that hides the wizard. Never write without one: a
  // wildcard would overwrite a concurrent change.
  if (editETag.value === null) {
    return { ok: false, error: failureMessage.value }
  }
  return await updateAlert(
    configurationName,
    model.value,
    props.folder_paths,
    props.prediction_periods,
    editETag.value
  )
}

async function saveAlert(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await persist()
    if (result.ok) {
      window.location.href = props.activate_changes_url
    } else {
      saveError.value = result.error
    }
  } catch {
    saveError.value = failureMessage.value
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mode-alerts-alert-wizard-app">
    <CmkAlert
      v-if="props.prefill_error"
      variant="warning"
      :text="untranslated(props.prefill_error)"
    />
    <CmkAlert v-if="loadError" variant="error" :text="untranslated(loadError)" />
    <CmkWizard v-else-if="!loading" v-model="currentStep" mode="guided">
      <NameStep v-if="!editing" v-model="model" :index="1" :is-completed="() => currentStep > 1" />

      <ServicesStep
        v-model="model"
        :conditions-spec="conditions_form.spec"
        :folder-paths="folder_paths"
        :index="2"
        :is-completed="() => currentStep > 2"
        :is-first="editing"
        :prefilled="editing || prefill !== null"
        :match-may-select-others="matchMaySelectOthers"
      />

      <ThresholdsStep
        v-model="model"
        :thresholds-spec="thresholds_form.spec"
        :time-picker="time_picker"
        :level-colors="{ warning: warning_color, critical: critical_color }"
        :finish-label="finishLabel"
        :saving="saving"
        :save-error="saveError"
        :index="3"
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
