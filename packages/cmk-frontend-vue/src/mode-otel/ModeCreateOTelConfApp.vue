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
import type {
  AuthConfig,
  EndpointConfig,
  EventConsoleConfig
} from './otel-configuration-steps/ConfigureCollector.vue'
import ConfigureGeneralProperties from './otel-configuration-steps/ConfigureGeneralProperties.vue'
import ConfigureHosts from './otel-configuration-steps/ConfigureHosts.vue'

const props = defineProps<{
  no_auth_allowed: boolean
  endpoint_config_allowed: boolean
  encryption_allowed: boolean
  event_console_allowed: boolean
}>()

const { _t } = usei18n()
const currentMode = ref<'guided' | 'overview'>('guided')
const currentStep = ref(1)

const configName = ref<string>('')
const siteId = ref<string | null>(null)

const generalPropertiesRef =
  useTemplateRef<InstanceType<typeof ConfigureGeneralProperties>>('generalProperties')

async function validateGeneralProperties(): Promise<boolean> {
  return (await generalPropertiesRef.value?.validate()) ?? false
}

const collectorRef = useTemplateRef<InstanceType<typeof ConfigureCollector>>('collector')

async function validateCollector(): Promise<boolean> {
  return collectorRef.value?.validate() ?? false
}

const grpcAuth = ref<AuthConfig>({
  method: props.no_auth_allowed ? 'none' : 'basicauth',
  credential: null
})
const httpAuth = ref<AuthConfig>({
  method: props.no_auth_allowed ? 'none' : 'basicauth',
  credential: null
})
const grpcEndpoint = ref<EndpointConfig>({ address: '', port: undefined })
const httpEndpoint = ref<EndpointConfig>({ address: '', port: undefined })
const grpcEncryption = ref<boolean>(false)
const httpEncryption = ref<boolean>(false)
const grpcEventConsole = ref<EventConsoleConfig | null>(null)
const httpEventConsole = ref<EventConsoleConfig | null>(null)

const close = () => {
  // TODO: trigger activate changes
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
          :config-name-placeholder="_t('opentelemetry_config_1')"
          config-list-endpoint="api/internal/domain-types/otel_collector_config_receivers/collections/all"
          :already-configured-error="
            _t(
              'OpenTelemetry is already configured for this site. Select another site or update the existing configuration.'
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
          {{ _t('Configure OpenTelemetry Collector') }}
        </CmkHeading>
        <CmkParagraph>{{
          _t('Configure at least one OpenTelemetry Collector receiver.')
        }}</CmkParagraph>
      </template>
      <template #content>
        <ConfigureCollector
          ref="collector"
          v-model:grpc-auth="grpcAuth"
          v-model:http-auth="httpAuth"
          v-model:grpc-endpoint="grpcEndpoint"
          v-model:http-endpoint="httpEndpoint"
          v-model:grpc-encryption="grpcEncryption"
          v-model:http-encryption="httpEncryption"
          v-model:grpc-event-console="grpcEventConsole"
          v-model:http-event-console="httpEventConsole"
          :no-auth-allowed="no_auth_allowed"
          :endpoint-config-allowed="endpoint_config_allowed"
          :encryption-allowed="encryption_allowed"
          :event-console-allowed="event_console_allowed"
        />
      </template>
      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateCollector" />
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
