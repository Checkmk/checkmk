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

import ConfigureCollector from './otel-configuration-steps/ConfigureCollector.vue'
import ConfigureGeneralProperties from './otel-configuration-steps/ConfigureGeneralProperties.vue'
import ConfigureInstrumentation from './otel-configuration-steps/ConfigureInstrumentation.vue'
import FinalizeConfiguration, {
  type FinalizeState
} from './otel-configuration-steps/FinalizeConfiguration.vue'
import OTelConfigurationSummary from './otel-configuration-steps/OTelConfigurationSummary.vue'
import {
  type AuthConfig,
  type EndpointConfig,
  type EventConsoleConfig,
  GRPC_DEFAULT_PORT,
  HTTP_DEFAULT_PORT
} from './otel-configuration-steps/otelTypes'
import type { PasswordConfig } from './otel-configuration-steps/password_store_password.types.ts'
import {
  type OTelAuthInput,
  type OTelBundleInput,
  type OTelReceiverProtocolInput,
  type OTelSocketAddressInput,
  POST_SAVE_ACTIONS,
  type PostSaveAction,
  createOTelBundleAction,
  createOTelReceiverConfigAction
} from './otel-configuration-steps/post_save_actions.ts'

const props = defineProps<{
  no_auth_allowed: boolean
  endpoint_config_allowed: boolean
  encryption_allowed: boolean
  event_console_allowed: boolean
  collector_activation_allowed: boolean
  metric_backend_allowed: boolean
  overview_url: string
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
const grpcEndpoint = ref<EndpointConfig>({
  socketAddressType: 'default_ipv4',
  address: '',
  port: undefined
})
const httpEndpoint = ref<EndpointConfig>({
  socketAddressType: 'default_ipv4',
  address: '',
  port: undefined
})
const grpcEnabled = ref<boolean>(true)
const httpEnabled = ref<boolean>(false)
const grpcEncryption = ref<boolean>(false)
const httpEncryption = ref<boolean>(false)
const grpcEventConsole = ref<EventConsoleConfig | null>(null)
const httpEventConsole = ref<EventConsoleConfig | null>(null)
const pendingPasswords = ref<Map<string, PasswordConfig>>(new Map())

// Pending passwords actually referenced by the configured auth methods. The
// Step 2 slide-in lets users create passwords they may later swap out, and we
// only want to persist the ones still selected when the wizard is finalized
const passwordsToSave = computed<PasswordConfig[]>(() => {
  const selectedIds = new Set<string>()
  if (grpcAuth.value.credential?.password) {
    selectedIds.add(grpcAuth.value.credential.password)
  }
  if (httpAuth.value.credential?.password) {
    selectedIds.add(httpAuth.value.credential.password)
  }
  return Array.from(pendingPasswords.value.values()).filter((p) =>
    selectedIds.has(p.general_props.id)
  )
})

const finalizeRef = useTemplateRef<InstanceType<typeof FinalizeConfiguration>>('finalize')

/**
 * Narrow the wizard's `AuthConfig` (which allows a null credential while the
 * form is being filled) into the create action's `OTelAuthInput`. Returns
 * `null` if `basicauth` is selected without a username or password id, which
 * tells `buildProtocolInput` to omit this protocol entirely.
 */
function narrowAuth(auth: AuthConfig): OTelAuthInput | null {
  switch (auth.method) {
    case 'none':
      return { method: 'none' }
    case 'basicauth': {
      const username = auth.credential?.username.trim()
      const passwordId = auth.credential?.password
      if (!username || !passwordId) {
        return null
      }
      return { method: 'basicauth', username, passwordId }
    }
  }
}

/**
 * Narrow the wizard's `EndpointConfig` (which allows `port: undefined` for
 * default modes) into the create action's `OTelSocketAddressInput`. Mirrors
 * `endpointIsConfigured` in `ConfigureCollector.vue` so the wizard validation
 * rule and the save gate agree: default IPv4/IPv6 are always considered
 * configured (the server resolves the bind), only `'custom'` requires the
 * user-entered address + port.
 */
function narrowSocketAddress(endpoint: EndpointConfig): OTelSocketAddressInput | null {
  switch (endpoint.socketAddressType) {
    case 'default_ipv4':
    case 'default_ipv6':
      return { type: endpoint.socketAddressType }
    case 'custom': {
      const address = endpoint.address.trim()
      if (!address || endpoint.port === undefined) {
        return null
      }
      return { type: 'custom', address, port: endpoint.port }
    }
  }
}

function isPasswordNew(auth: AuthConfig): boolean {
  const id = auth.credential?.password
  return id !== null && id !== undefined && pendingPasswords.value.has(id)
}

function buildProtocolInput(
  auth: AuthConfig,
  endpoint: EndpointConfig,
  encryption: boolean,
  eventConsole: EventConsoleConfig | null
): OTelReceiverProtocolInput | null {
  const narrowedAuth = narrowAuth(auth)
  if (!narrowedAuth) {
    return null
  }
  if (!props.endpoint_config_allowed) {
    return { auth: narrowedAuth }
  }
  const socketAddress = narrowSocketAddress(endpoint)
  if (!socketAddress) {
    return null
  }
  return {
    auth: narrowedAuth,
    extended: {
      socketAddress,
      encryption,
      eventConsole: props.event_console_allowed ? eventConsole : null
    }
  }
}

// Per-run create action plus the shared post-save list, with edition-specific
// activation steps stripped on cloud. Composed here (not in
// `FinalizeConfiguration`) so the renderer stays purely visual.
const finalizeActions = computed<readonly PostSaveAction[]>(() => {
  if (!siteId.value) {
    return []
  }
  const sharedActions = POST_SAVE_ACTIONS.filter((action) => {
    if (!props.collector_activation_allowed && action.key === 'enableCollector') {
      return false
    }
    if (!props.metric_backend_allowed && action.key === 'enableMetricBackend') {
      return false
    }
    return true
  })
  // The per-protocol enable checkboxes (`grpcEnabled` / `httpEnabled`) gate the
  // save payload here so the disabled tab's form state never reaches the
  // server, matching what the wizard shows the user.
  const bundleInput: OTelBundleInput = {
    configName: configName.value,
    siteId: siteId.value,
    passwordIds: passwordsToSave.value.map((p) => p.general_props.id)
  }
  return [
    ...sharedActions.slice(0, -1),
    createOTelReceiverConfigAction({
      id: configName.value,
      siteId: siteId.value,
      grpc: grpcEnabled.value
        ? buildProtocolInput(
            grpcAuth.value,
            grpcEndpoint.value,
            grpcEncryption.value,
            grpcEventConsole.value
          )
        : null,
      http: httpEnabled.value
        ? buildProtocolInput(
            httpAuth.value,
            httpEndpoint.value,
            httpEncryption.value,
            httpEventConsole.value
          )
        : null,
      passwords: passwordsToSave.value
    }),
    ...sharedActions.slice(-1),
    createOTelBundleAction(bundleInput)
  ]
})

/**
 * State machine driving the Step 4 save button. Updated by
 * `FinalizeConfiguration`'s `update:state` emit:
 *   - 'idle'    : initial — label "Save OpenTelemetry configuration"
 *   - 'running' : running post-save actions — button disabled
 *   - 'success' : all post-save actions ok — label "Finish & go to Activate changes"
 *   - 'error'   : at least one post-save action failed — label stays as "Save..." so the
 *                 user can retry after fixing the problem
 */
const saveState = ref<FinalizeState>('idle')

const saveButtonLabel = computed(() =>
  saveState.value === 'success'
    ? _t('Finish & go to Activate changes')
    : _t('Save OpenTelemetry configuration')
)

const saveButtonDisabled = computed(() => saveState.value === 'running')

async function onSaveClick(): Promise<void> {
  // Second click after a successful run navigates back to the OTel Overview
  // page and opens the "Activate changes" panel so the user can apply the
  // pending configuration changes.
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
          v-model:grpc-enabled="grpcEnabled"
          v-model:http-enabled="httpEnabled"
          v-model:grpc-auth="grpcAuth"
          v-model:http-auth="httpAuth"
          v-model:grpc-endpoint="grpcEndpoint"
          v-model:http-endpoint="httpEndpoint"
          v-model:grpc-encryption="grpcEncryption"
          v-model:http-encryption="httpEncryption"
          v-model:grpc-event-console="grpcEventConsole"
          v-model:http-event-console="httpEventConsole"
          v-model:pending-passwords="pendingPasswords"
          :no-auth-allowed="no_auth_allowed"
          :endpoint-config-allowed="endpoint_config_allowed"
          :encryption-allowed="encryption_allowed"
          :event-console-allowed="event_console_allowed"
          :grpc-default-port="GRPC_DEFAULT_PORT"
          :http-default-port="HTTP_DEFAULT_PORT"
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
          {{ _t('Adjust your OpenTelemetry instrumentation') }}
        </CmkHeading>

        <CmkParagraph>{{
          _t(
            'This step guides the user through configuring their OpenTelemetry instrumentation so that telemetry data can be sent to Checkmk.'
          )
        }}</CmkParagraph>
      </template>
      <template #content>
        <ConfigureInstrumentation
          :site-name="siteId ?? ''"
          :grpc-enabled="grpcEnabled"
          :http-enabled="httpEnabled"
          :grpc-endpoint="grpcEndpoint"
          :http-endpoint="httpEndpoint"
          :grpc-tls-enabled="grpcEncryption"
          :http-tls-enabled="httpEncryption"
          :grpc-auth="grpcAuth"
          :http-auth="httpAuth"
          :grpc-event-console="grpcEventConsole"
          :http-event-console="httpEventConsole"
        />
      </template>

      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateCollector" />
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="4" :is-completed="() => currentStep > 4">
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
          @update:state="saveState = $event"
        >
          <template #success-summary>
            <OTelConfigurationSummary
              v-if="siteId !== null"
              :config-name="configName"
              :site-id="siteId"
              :grpc-enabled="grpcEnabled"
              :http-enabled="httpEnabled"
              :grpc-auth="grpcAuth"
              :http-auth="httpAuth"
              :grpc-endpoint="grpcEndpoint"
              :http-endpoint="httpEndpoint"
              :grpc-encryption="grpcEncryption"
              :http-encryption="httpEncryption"
              :grpc-event-console="grpcEventConsole"
              :http-event-console="httpEventConsole"
              :grpc-password-is-new="isPasswordNew(grpcAuth)"
              :http-password-is-new="isPasswordNew(httpAuth)"
              :endpoint-config-allowed="endpoint_config_allowed"
              :encryption-allowed="encryption_allowed"
              :event-console-allowed="event_console_allowed"
            />
          </template>
        </FinalizeConfiguration>
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
