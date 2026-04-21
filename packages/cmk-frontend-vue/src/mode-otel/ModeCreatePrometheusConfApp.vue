<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ConfigureGeneralProperties from './otel-configuration-steps/ConfigureGeneralProperties.vue'
import ConfigurePrometheusScraper from './otel-configuration-steps/ConfigurePrometheusScraper.vue'
import type { PrometheusScraperConfig } from './otel-configuration-steps/ConfigurePrometheusScraper.vue'
import FinalizeConfiguration, {
  type FinalizeState
} from './otel-configuration-steps/FinalizeConfiguration.vue'

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

const saveButtonLabel = computed(() =>
  saveState.value === 'success'
    ? _t('Finish & go to Activate changes')
    : _t('Save Prometheus configuration')
)

const saveButtonDisabled = computed(() => saveState.value === 'running')

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
  await finalizeRef.value?.runActions()
}
</script>

<template>
  <CmkWizardModeToggle v-model="currentMode" />
  <CmkWizard v-model="currentStep" :mode="currentMode">
    <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
      <template #header>
        <CmkHeading>
          {{ _t('Configure title and site') }}
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
          :config-name-placeholder="_t('prometheus_config_1')"
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
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="3" :is-completed="() => currentStep > 3">
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
          :running-message="_t('Verifying the Prometheus configuration...')"
          :success-message="_t('Prometheus configuration saved successfully.')"
          :error-heading="_t('Could not save the Prometheus configuration')"
          @update:state="saveState = $event"
        />
      </template>
      <template #actions>
        <CmkWizardButton
          type="finish"
          :override-label="saveButtonLabel"
          :disabled="saveButtonDisabled"
          @click="onSaveClick"
        />
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>
