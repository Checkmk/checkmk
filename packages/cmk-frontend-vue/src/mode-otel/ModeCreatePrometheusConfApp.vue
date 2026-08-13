<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef, watch } from 'vue'

import ConfigureGeneralProperties from './otel-configuration-steps/ConfigureGeneralProperties.vue'
import ConfigurePrometheusScraper from './otel-configuration-steps/ConfigurePrometheusScraper.vue'
import type { PrometheusScraperConfig } from './otel-configuration-steps/ConfigurePrometheusScraper.vue'
import FinalizeConfiguration, {
  type FinalizeState
} from './otel-configuration-steps/FinalizeConfiguration.vue'
import PrometheusConfigurationSummary from './otel-configuration-steps/PrometheusConfigurationSummary.vue'
import {
  type PostSaveAction,
  buildPrometheusFinalizeActions
} from './otel-configuration-steps/post_save_actions.ts'

const props = defineProps<{
  overview_url: string
}>()

const { _t } = usei18n()
const currentMode = ref<'guided' | 'overview'>('guided')
const currentStep = ref(1)

const configName = ref<string>('')
const siteId = ref<string | null>(null)
const scraperConfig = ref<PrometheusScraperConfig>({
  jobName: '',
  metricsPath: '',
  address: '',
  port: undefined,
  encryption: false
})

const generalPropertiesRef =
  useTemplateRef<InstanceType<typeof ConfigureGeneralProperties>>('generalProperties')
const prometheusScraperRef =
  useTemplateRef<InstanceType<typeof ConfigurePrometheusScraper>>('prometheusScraper')

async function validateGeneralProperties(): Promise<boolean> {
  return (await generalPropertiesRef.value?.validate()) ?? false
}

async function validatePrometheusScraper(): Promise<boolean> {
  return prometheusScraperRef.value?.validate() ?? false
}

const finalizeRef = useTemplateRef<InstanceType<typeof FinalizeConfiguration>>('finalize')

// Per-run create action plus the shared post-save list, in the order the
// checklist should display. Composition lives in `buildPrometheusFinalizeActions`
// so the order is testable without mounting this component.
const finalizeActions = computed<readonly PostSaveAction[]>(() => {
  // Port is validated in Step 2 (ConfigurePrometheusScraper.validate) before
  // the user can reach Step 3, so by the time the save button runs we can
  // safely assume it is defined. Guard anyway so an unexpected state surfaces
  // an empty action list rather than a request with NaN port.
  if (!siteId.value || scraperConfig.value.port === undefined) {
    return []
  }
  return buildPrometheusFinalizeActions({
    id: configName.value,
    siteId: siteId.value,
    jobName: scraperConfig.value.jobName,
    metricsPath: scraperConfig.value.metricsPath,
    address: scraperConfig.value.address,
    port: scraperConfig.value.port,
    encryption: scraperConfig.value.encryption
  })
})

/**
 * State machine driving the Step 3 save button. Updated by
 * `FinalizeConfiguration`'s `update:state` emit:
 *   - 'idle'    : initial — label "Save Prometheus configuration"
 *   - 'running' : running post-save actions — button disabled
 *   - 'success' : all post-save actions ok — label "Finish & go to Activate changes"
 *   - 'error'   : at least one post-save action failed — label stays as "Save..." so the
 *                 user can retry after fixing the problem
 */
const saveState = ref<FinalizeState>('idle')

// Single source of truth for the finalize-step index — also bound to the
// matching <CmkWizardStep :index="STEP_FINALIZE"> in the template, so adding
// or reordering steps cannot silently desynchronise the watch below.
const STEP_FINALIZE = 3

// Once the post-save actions succeed, the configs already exist on the
// backend. Force the user back to the finalize step in guided mode so they
// cannot edit earlier-step form fields — which would otherwise look editable
// but never get saved. The wizard's `locked` binding below also disables
// Previous / step-badge navigation.
watch(saveState, (value) => {
  if (value === 'success' && currentMode.value !== 'overview') {
    currentMode.value = 'guided'
    currentStep.value = STEP_FINALIZE
  }
})

// Hide the mode toggle and the Previous buttons once the save succeeds, so
// the user cannot route around the wizard's `locked` binding visually.
const showBackControls = computed(() => saveState.value !== 'success')

const saveButtonLabel = computed(() =>
  saveState.value === 'success'
    ? _t('Finish & go to Activate changes')
    : _t('Save Prometheus configuration')
)

const saveButtonDisabled = computed(() => saveState.value === 'running')

// In overview mode all steps are validated on save (the per-step Next buttons
// are hidden). When that validation fails we surface this message above the
// finalize button so the user knows why the save did not proceed.
const overviewValidationFailed = ref(false)

async function onSaveClick(): Promise<void> {
  // Second click after a successful run navigates back to the Prometheus
  // Overview page and opens the "Activate changes" panel so the user can
  // apply the pending configuration changes.
  if (saveState.value === 'success') {
    // Open the main-menu "Changes" panel in the top frame. The nav item is
    // rendered by MainMenuApp with id="nav-item-changes"; clicking it toggles
    // the activate-changes slide-in. We trigger it before navigating so the
    // panel is already visible when the overview page loads.
    try {
      const changesNavItem = top?.document.getElementById('nav-item-changes')
      changesNavItem?.click()
    } catch {
      // Cross-origin or missing element — fall through to navigation.
    }
    window.location.href = props.overview_url
    return
  }
  // In overview mode the per-step Next buttons (which normally carry
  // validation callbacks) are hidden, so we must validate all steps here
  // before handing off to the save actions.
  if (currentMode.value === 'overview') {
    const [generalValid, scraperValid] = await Promise.all([
      validateGeneralProperties(),
      validatePrometheusScraper()
    ])
    if (!generalValid || !scraperValid) {
      overviewValidationFailed.value = true
      return
    }
    overviewValidationFailed.value = false
  }
  await finalizeRef.value?.runActions()
}
</script>

<template>
  <CmkWizardModeToggle v-if="showBackControls" v-model="currentMode" />
  <CmkWizard v-model="currentStep" :mode="currentMode" :locked="!showBackControls">
    <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
      <template #header>
        <CmkHeading>
          {{ _t('General configuration properties') }}
        </CmkHeading>
        <CmkParagraph>{{
          _t(
            'Set the configuration name and select the site the OpenTelemetry Collector will run on.'
          )
        }}</CmkParagraph>
      </template>
      <template #content>
        <ConfigureGeneralProperties
          ref="generalProperties"
          v-model:config-name="configName"
          v-model:site-id="siteId"
          config-name-prefix="prometheus_config_"
          config-list-endpoint="api/internal/domain-types/otel_collector_config_prom_scrape/collections/all"
          :already-configured-error="
            _t(
              'Prometheus is already configured for this site. Select another site or update the existing configuration.'
            )
          "
        />
      </template>
      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateGeneralProperties" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
      <template #header>
        <CmkHeading>
          {{ _t('Configure scraper') }}
        </CmkHeading>
        <CmkParagraph>{{ _t('Specify the Prometheus target you want to scrape.') }}</CmkParagraph>
      </template>
      <template #content>
        <ConfigurePrometheusScraper ref="prometheusScraper" v-model:config="scraperConfig" />
      </template>
      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validatePrometheusScraper" />
        <CmkWizardButton v-if="showBackControls" type="previous" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="STEP_FINALIZE" :is-completed="() => currentStep > STEP_FINALIZE">
      <template #header>
        <CmkHeading>
          {{ _t('Finalize configuration') }}
        </CmkHeading>

        <CmkParagraph>{{ _t('Get your configuration ready to be applied.') }}</CmkParagraph>
      </template>
      <template #content>
        <FinalizeConfiguration
          ref="finalize"
          :site-id="siteId"
          :config-name="configName"
          :actions="finalizeActions"
          :running-message="_t('Verifying the Prometheus configuration...')"
          :success-message="_t('Prometheus configuration saved successfully.')"
          :error-heading="_t('Could not save the Prometheus configuration')"
          @update:state="saveState = $event"
        >
          <template #success-summary>
            <PrometheusConfigurationSummary
              v-if="scraperConfig.port !== undefined && siteId !== null"
              :config-name="configName"
              :site-id="siteId"
              :job-name="scraperConfig.jobName"
              :metrics-path="scraperConfig.metricsPath"
              :address="scraperConfig.address"
              :port="scraperConfig.port"
              :encryption="scraperConfig.encryption"
            />
          </template>
        </FinalizeConfiguration>
      </template>
      <template #actions>
        <div class="mode-otel-mode-create-prometheus-conf-app__actions">
          <CmkAlertBox v-if="overviewValidationFailed" variant="error" size="small">
            {{ _t('The form still contains invalid data. Please correct them and try again.') }}
          </CmkAlertBox>
          <div class="mode-otel-mode-create-prometheus-conf-app__actions-buttons">
            <CmkWizardButton
              type="finish"
              :override-label="saveButtonLabel"
              :disabled="saveButtonDisabled"
              @click="onSaveClick"
            />
            <CmkWizardButton v-if="showBackControls" type="previous" />
          </div>
        </div>
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>

<style scoped>
.mode-otel-mode-create-prometheus-conf-app__actions {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.mode-otel-mode-create-prometheus-conf-app__actions-buttons {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
