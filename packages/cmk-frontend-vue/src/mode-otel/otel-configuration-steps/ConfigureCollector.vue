<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import CollectorAuthConfig from './CollectorAuthConfig.vue'
import CollectorConnectionOptions from './CollectorConnectionOptions.vue'
import CollectorEndpointConfig from './CollectorEndpointConfig.vue'
import PasswordStoreSlideIn from './PasswordStoreSlideIn.vue'
import type { AuthConfig, EndpointConfig, EventConsoleConfig } from './otelTypes'
import type { PasswordConfig } from './password_store_password.types.ts'
import { isValidIpOrHostname, isValidPort } from './validation.ts'

const { _t } = usei18n()
const createdSuffix = _t(' | created')

const props = defineProps<{
  noAuthAllowed: boolean
  endpointConfigAllowed: boolean
  encryptionAllowed: boolean
  eventConsoleAllowed: boolean
  grpcDefaultPort: number
  httpDefaultPort: number
}>()

const grpcEnabled = defineModel<boolean>('grpcEnabled', { required: true })
const httpEnabled = defineModel<boolean>('httpEnabled', { required: true })
const grpcAuth = defineModel<AuthConfig>('grpcAuth', { required: true })
const httpAuth = defineModel<AuthConfig>('httpAuth', { required: true })
const grpcEndpoint = defineModel<EndpointConfig>('grpcEndpoint', { required: true })
const httpEndpoint = defineModel<EndpointConfig>('httpEndpoint', { required: true })
const grpcEncryption = defineModel<boolean>('grpcEncryption', { required: true })
const httpEncryption = defineModel<boolean>('httpEncryption', { required: true })
const grpcEventConsole = defineModel<EventConsoleConfig | null>('grpcEventConsole', {
  required: true
})
const httpEventConsole = defineModel<EventConsoleConfig | null>('httpEventConsole', {
  required: true
})
const newlyCreatedPasswords = defineModel<Map<string, PasswordConfig>>('newlyCreatedPasswords', {
  required: true
})

const activeTab = ref('grpc')
const availablePasswords = ref<Suggestion[]>([])
const displayErrors = ref(false)
const passwordStoreSlideInOpen = ref(false)
const passwordTargetAuth = ref<'grpc' | 'http'>('grpc')

onMounted(async () => {
  try {
    const response = await fetchRestAPI(
      'api/v1/domain-types/passwordstore_password/collections/passwordstore_password',
      'GET'
    )
    const data = await response.json()
    const fetched: Suggestion[] = data.value.map((p: { id: string; title: string }) => ({
      name: p.id,
      title: p.title
    }))
    const created: Suggestion[] = Array.from(newlyCreatedPasswords.value.values()).map((p) => ({
      name: p.general_props.id,
      title: `${p.general_props.title}${createdSuffix}` as TranslatedString
    }))
    availablePasswords.value = fetched.concat(created)
  } catch {
    // password store unavailable — leave list empty
  }
})

const bothEndpointsEmpty = computed(
  () =>
    (!grpcEnabled.value || !endpointIsConfigured(grpcEndpoint.value)) &&
    (!httpEnabled.value || !endpointIsConfigured(httpEndpoint.value))
)

function getEffectivePort(endpoint: EndpointConfig, defaultPort: number): number | undefined {
  if (endpoint.socketAddressType !== 'custom') {
    return defaultPort
  }
  return isValidPort(endpoint.port) ? endpoint.port : undefined
}

const portsConflict = computed(() => {
  if (!grpcEnabled.value || !httpEnabled.value) {
    return false
  }
  const grpcPort = getEffectivePort(grpcEndpoint.value, props.grpcDefaultPort)
  const httpPort = getEffectivePort(httpEndpoint.value, props.httpDefaultPort)
  return grpcPort !== undefined && httpPort !== undefined && grpcPort === httpPort
})

function authHasErrors(auth: AuthConfig): boolean {
  return (
    auth.method === 'basicauth' && (!auth.credential?.username.trim() || !auth.credential?.password)
  )
}

function tlsHasErrors(auth: AuthConfig, encryption: boolean): boolean {
  return auth.method === 'basicauth' && !encryption
}

function eventConsoleHasErrors(ec: EventConsoleConfig | null): boolean {
  return ec !== null && !ec.resourceAttribute.trim()
}

function endpointIsConfigured(endpoint: EndpointConfig): boolean {
  if (endpoint.socketAddressType !== 'custom') {
    return true
  }
  return !!endpoint.address.trim() || endpoint.port !== undefined
}

function configuredEndpointHasErrors(endpoint: EndpointConfig): boolean {
  if (endpoint.socketAddressType !== 'custom') {
    return false
  }
  return !isValidIpOrHostname(endpoint.address) || !isValidPort(endpoint.port)
}

function endpointHasValidationErrors(endpoint: EndpointConfig, other: EndpointConfig): boolean {
  if (endpoint.socketAddressType !== 'custom') {
    return false
  }
  if (!endpoint.address.trim()) {
    return endpoint.port !== undefined || !endpointIsConfigured(other)
  }
  return configuredEndpointHasErrors(endpoint)
}

function tabHasValidationErrors(tab: 'grpc' | 'http'): boolean {
  const enabled = tab === 'grpc' ? grpcEnabled.value : httpEnabled.value
  if (!enabled) {
    return false
  }

  const auth = tab === 'grpc' ? grpcAuth.value : httpAuth.value
  const encryption = tab === 'grpc' ? grpcEncryption.value : httpEncryption.value
  const ec = tab === 'grpc' ? grpcEventConsole.value : httpEventConsole.value

  if (authHasErrors(auth)) {
    return true
  }
  if (props.encryptionAllowed && tlsHasErrors(auth, encryption)) {
    return true
  }
  if (props.eventConsoleAllowed && eventConsoleHasErrors(ec)) {
    return true
  }
  if (!props.endpointConfigAllowed) {
    return false
  }
  if (portsConflict.value) {
    return true
  }

  const endpoint = tab === 'grpc' ? grpcEndpoint.value : httpEndpoint.value
  const other = tab === 'grpc' ? httpEndpoint.value : grpcEndpoint.value
  return endpointHasValidationErrors(endpoint, other)
}

function validate(): boolean {
  displayErrors.value = true

  if (!grpcEnabled.value && !httpEnabled.value) {
    return false
  }

  const ecValid =
    (!grpcEnabled.value || !eventConsoleHasErrors(grpcEventConsole.value)) &&
    (!httpEnabled.value || !eventConsoleHasErrors(httpEventConsole.value))

  const tlsValid =
    !props.encryptionAllowed ||
    ((!grpcEnabled.value || !tlsHasErrors(grpcAuth.value, grpcEncryption.value)) &&
      (!httpEnabled.value || !tlsHasErrors(httpAuth.value, httpEncryption.value)))

  let isValid: boolean
  if (!props.endpointConfigAllowed) {
    isValid =
      (!grpcEnabled.value || !authHasErrors(grpcAuth.value)) &&
      (!httpEnabled.value || !authHasErrors(httpAuth.value)) &&
      ecValid &&
      tlsValid
  } else {
    isValid =
      (!grpcEnabled.value ||
        !endpointHasValidationErrors(grpcEndpoint.value, httpEndpoint.value)) &&
      (!httpEnabled.value ||
        !endpointHasValidationErrors(httpEndpoint.value, grpcEndpoint.value)) &&
      (!grpcEnabled.value || !authHasErrors(grpcAuth.value)) &&
      (!httpEnabled.value || !authHasErrors(httpAuth.value)) &&
      !portsConflict.value &&
      ecValid &&
      tlsValid
  }

  if (!isValid) {
    if (
      activeTab.value === 'grpc' &&
      !tabHasValidationErrors('grpc') &&
      tabHasValidationErrors('http')
    ) {
      activeTab.value = 'http'
    } else if (
      activeTab.value === 'http' &&
      !tabHasValidationErrors('http') &&
      tabHasValidationErrors('grpc')
    ) {
      activeTab.value = 'grpc'
    }
  }

  return isValid
}

function openPasswordSlideIn(target: 'grpc' | 'http') {
  passwordTargetAuth.value = target
  passwordStoreSlideInOpen.value = true
}

function onPasswordCreated(password: PasswordConfig) {
  passwordStoreSlideInOpen.value = false
  newlyCreatedPasswords.value.set(password.general_props.id, password)
  availablePasswords.value.push({
    name: password.general_props.id,
    title: `${password.general_props.title}${createdSuffix}` as TranslatedString
  })
  const triggeringAuth = passwordTargetAuth.value === 'grpc' ? grpcAuth.value : httpAuth.value
  if (triggeringAuth.credential !== null) {
    triggeringAuth.credential.password = password.general_props.id
  }
  const otherAuth = passwordTargetAuth.value === 'grpc' ? httpAuth.value : grpcAuth.value
  if (otherAuth.credential !== null && !otherAuth.credential.password) {
    otherAuth.credential.password = password.general_props.id
  }
}

defineExpose({ validate, onPasswordCreated })
</script>

<template>
  <CmkInlineValidation
    v-if="displayErrors && !grpcEnabled && !httpEnabled"
    :validation="[_t('At least one receiver (GRPC or HTTP) must be enabled.')]"
  />

  <CmkTabs v-model="activeTab">
    <template #tabs>
      <CmkTab id="grpc">{{ _t('GRPC') }}</CmkTab>
      <CmkTab id="http">{{ _t('HTTP') }}</CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent id="grpc">
        <div class="mode-otel-configure-collector__form">
          <CmkParagraph class="mode-otel-configure-collector__tab-description">{{
            _t('Configure a GRPC-based OTLP receiver that will collect OpenTelemetry data.')
          }}</CmkParagraph>
          <CmkLabel>{{ _t('Enable the GRPC-based OTLP receiver') }}</CmkLabel>
          <CmkCheckbox v-model="grpcEnabled" />
          <div
            :class="[
              'mode-otel-configure-collector__tab-body',
              { 'mode-otel-configure-collector__tab-body--disabled': !grpcEnabled }
            ]"
          >
            <CollectorEndpointConfig
              v-if="endpointConfigAllowed"
              v-model:endpoint="grpcEndpoint"
              :show-errors="displayErrors"
              :both-endpoints-empty="bothEndpointsEmpty"
              :port-conflict="portsConflict"
              :default-port="grpcDefaultPort"
            />
            <CollectorAuthConfig
              v-model:auth="grpcAuth"
              :no-auth-allowed="noAuthAllowed"
              :available-passwords="availablePasswords"
              :show-errors="displayErrors"
              @create-password="openPasswordSlideIn('grpc')"
            />
            <CollectorConnectionOptions
              v-model:encryption="grpcEncryption"
              v-model:event-console="grpcEventConsole"
              :encryption-allowed="encryptionAllowed"
              :event-console-allowed="eventConsoleAllowed"
              :show-errors="displayErrors"
              :tls-required="displayErrors && tlsHasErrors(grpcAuth, grpcEncryption)"
            />
          </div>
        </div>
      </CmkTabContent>

      <CmkTabContent id="http">
        <div class="mode-otel-configure-collector__form">
          <CmkParagraph class="mode-otel-configure-collector__tab-description">{{
            _t('Configure an HTTP-based OTLP receiver that will collect OpenTelemetry data.')
          }}</CmkParagraph>
          <CmkLabel>{{ _t('Enable the HTTP-based OTLP receiver') }}</CmkLabel>
          <CmkCheckbox v-model="httpEnabled" />
          <div
            :class="[
              'mode-otel-configure-collector__tab-body',
              { 'mode-otel-configure-collector__tab-body--disabled': !httpEnabled }
            ]"
          >
            <CollectorEndpointConfig
              v-if="endpointConfigAllowed"
              v-model:endpoint="httpEndpoint"
              :show-errors="displayErrors"
              :both-endpoints-empty="bothEndpointsEmpty"
              :port-conflict="portsConflict"
              :default-port="httpDefaultPort"
            />
            <CollectorAuthConfig
              v-model:auth="httpAuth"
              :no-auth-allowed="noAuthAllowed"
              :available-passwords="availablePasswords"
              :show-errors="displayErrors"
              @create-password="openPasswordSlideIn('http')"
            />
            <CollectorConnectionOptions
              v-model:encryption="httpEncryption"
              v-model:event-console="httpEventConsole"
              :encryption-allowed="encryptionAllowed"
              :event-console-allowed="eventConsoleAllowed"
              :show-errors="displayErrors"
              :tls-required="displayErrors && tlsHasErrors(httpAuth, httpEncryption)"
            />
          </div>
        </div>
      </CmkTabContent>
    </template>
  </CmkTabs>

  <PasswordStoreSlideIn
    :open="passwordStoreSlideInOpen"
    @close="passwordStoreSlideInOpen = false"
    @created="onPasswordCreated"
  />
</template>

<style scoped>
.mode-otel-configure-collector__form {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;
  margin-top: var(--spacing);
}

.mode-otel-configure-collector__tab-body {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: subgrid;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;

  &.mode-otel-configure-collector__tab-body--disabled {
    opacity: 0.5;
    pointer-events: none;
    user-select: none;
  }
}

.mode-otel-configure-collector__tab-description {
  grid-column: 1 / -1;
}
</style>
