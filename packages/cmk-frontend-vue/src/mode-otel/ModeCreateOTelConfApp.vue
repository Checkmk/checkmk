<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ConfigureCollector from './otel-configuration-steps/ConfigureCollector.vue'
import ConfigureGeneralProperties from './otel-configuration-steps/ConfigureGeneralProperties.vue'
import ConfigureHosts from './otel-configuration-steps/ConfigureHosts.vue'

const { _t } = usei18n()
const currentMode = ref<'guided' | 'overview'>('guided')
const currentStep = ref(1)

const configName = ref<string>('')
const siteId = ref<string | null>(null)

const generalPropertiesRef =
  useTemplateRef<InstanceType<typeof ConfigureGeneralProperties>>('generalProperties')

async function validateGeneralProperties(): Promise<boolean> {
  return generalPropertiesRef.value?.validate() ?? false
}

const close = () => {
  console.log('Activate changes')
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
        />
      </template>
      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateGeneralProperties" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
      <template #header>
        <CmkHeading>
          {{ _t('Configure OpenTelemetry collector') }}
        </CmkHeading>
        <CmkParagraph>{{
          _t('Configure at least one OpenTelemetry Collector receiver.')
        }}</CmkParagraph>
      </template>
      <template #content>
        <ConfigureCollector />
      </template>
      <template #actions>
        <CmkWizardButton type="next" />
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="3" :is-completed="() => currentStep > 3">
      <template #header>
        <CmkHeading>
          {{ _t('Configure host folder') }}
        </CmkHeading>
      </template>
      <template #content>
        <ConfigureHosts />
      </template>
      <template #actions>
        <CmkWizardButton
          type="finish"
          :override-label="_t('Save & Go to Activate Changes')"
          @click="close"
        />
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>
