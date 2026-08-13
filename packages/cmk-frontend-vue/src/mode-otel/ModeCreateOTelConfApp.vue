<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef, watch } from 'vue'

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
  may_create_password: boolean
  overview_url: string
  cloud_grpc_receiver_endpoint?: string | null
  cloud_http_receiver_endpoint?: string | null
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
const availablePasswords = ref<Suggestion[]>([])

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
 * `configuredEndpointHasErrors` in `ConfigureCollector.vue` so the wizard
 * validation rule and the save gate agree: default IPv4/IPv6 are always
 * accepted (the server resolves the bind), only `'custom'` requires the
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

function passwordTitle(auth: AuthConfig): string {
  const id = auth.credential?.password
  if (!id) {
    return ''
  }
  const pending = pendingPasswords.value.get(id)
  if (pending) {
    return pending.general_props.title
  }
  return availablePasswords.value.find((p) => p.name === id)?.title ?? id
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

// Single source of truth for the finalize-step index — also bound to the
// matching <CmkWizardStep :index="STEP_FINALIZE"> in the template, so adding
// or reordering steps cannot silently desynchronise the watch below.
const STEP_FINALIZE = 4

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
    : _t('Save OpenTelemetry configuration')
)

const saveButtonDisabled = computed(() => saveState.value === 'running')

// In overview mode all steps are validated on save (the per-step Next buttons
// are hidden). When that validation fails we surface this message above the
// finalize button so the user knows why the save did not proceed.
const overviewValidationFailed = ref(false)

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
  // In overview mode the per-step Next buttons (which normally carry
  // validation callbacks) are hidden, so we must validate all steps here
  // before handing off to the save actions.
  if (currentMode.value === 'overview') {
    const [generalValid, collectorValid] = await Promise.all([
      validateGeneralProperties(),
      validateCollector()
    ])
    if (!generalValid || !collectorValid) {
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
          config-name-prefix="opentelemetry_config_"
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
          v-model:available-passwords="availablePasswords"
          :no-auth-allowed="no_auth_allowed"
          :endpoint-config-allowed="endpoint_config_allowed"
          :encryption-allowed="encryption_allowed"
          :event-console-allowed="event_console_allowed"
          :may-create-password="may_create_password"
          :grpc-default-port="GRPC_DEFAULT_PORT"
          :http-default-port="HTTP_DEFAULT_PORT"
        />
      </template>
      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateCollector" />
        <CmkWizardButton v-if="showBackControls" type="previous" />
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
          :cloud-grpc-endpoint="cloud_grpc_receiver_endpoint ?? null"
          :cloud-http-endpoint="cloud_http_receiver_endpoint ?? null"
        />
      </template>

      <template #actions>
        <CmkWizardButton type="next" :validation-cb="validateCollector" />
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
              :grpc-password-name="passwordTitle(grpcAuth)"
              :http-password-name="passwordTitle(httpAuth)"
              :endpoint-config-allowed="endpoint_config_allowed"
              :encryption-allowed="encryption_allowed"
              :event-console-allowed="event_console_allowed"
            />
          </template>
        </FinalizeConfiguration>
      </template>
      <template #actions>
        <div class="mode-otel-mode-create-o-tel-conf-app__actions">
          <CmkAlertBox v-if="overviewValidationFailed" variant="error" size="small">
            {{ _t('The form still contains invalid data. Please correct them and try again.') }}
          </CmkAlertBox>
          <div class="mode-otel-mode-create-o-tel-conf-app__actions-buttons">
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
.mode-otel-mode-create-o-tel-conf-app__actions {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.mode-otel-mode-create-o-tel-conf-app__actions-buttons {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
