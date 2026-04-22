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

import type { Suggestion } from '@/components/CmkSuggestions'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

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
}>()

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
  () => !endpointIsConfigured(grpcEndpoint.value) && !endpointIsConfigured(httpEndpoint.value)
)

const portsConflict = computed(() => {
  const grpcPort = grpcEndpoint.value.port
  const httpPort = httpEndpoint.value.port
  return (
    grpcPort !== undefined &&
    httpPort !== undefined &&
    isValidPort(grpcPort) &&
    isValidPort(httpPort) &&
    grpcPort === httpPort
  )
})

function authHasErrors(auth: AuthConfig): boolean {
  return (
    auth.method === 'basicauth' && (!auth.credential?.username.trim() || !auth.credential?.password)
  )
}

function eventConsoleHasErrors(ec: EventConsoleConfig | null): boolean {
  return ec !== null && !ec.resourceAttribute.trim()
}

function endpointIsConfigured(endpoint: EndpointConfig): boolean {
  return !!endpoint.address.trim() || endpoint.port !== undefined
}

function configuredEndpointHasErrors(endpoint: EndpointConfig): boolean {
  return !isValidIpOrHostname(endpoint.address) || !isValidPort(endpoint.port)
}

function endpointHasValidationErrors(endpoint: EndpointConfig, other: EndpointConfig): boolean {
  if (!endpoint.address.trim()) {
    return endpoint.port !== undefined || !endpointIsConfigured(other)
  }
  return configuredEndpointHasErrors(endpoint)
}

function tabHasValidationErrors(tab: 'grpc' | 'http'): boolean {
  const auth = tab === 'grpc' ? grpcAuth.value : httpAuth.value
  const ec = tab === 'grpc' ? grpcEventConsole.value : httpEventConsole.value

  if (authHasErrors(auth)) {
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

  const ecValid =
    !eventConsoleHasErrors(grpcEventConsole.value) && !eventConsoleHasErrors(httpEventConsole.value)

  let isValid: boolean
  if (!props.endpointConfigAllowed) {
    isValid = !authHasErrors(grpcAuth.value) && !authHasErrors(httpAuth.value) && ecValid
  } else {
    isValid =
      !endpointHasValidationErrors(grpcEndpoint.value, httpEndpoint.value) &&
      !endpointHasValidationErrors(httpEndpoint.value, grpcEndpoint.value) &&
      !authHasErrors(grpcAuth.value) &&
      !authHasErrors(httpAuth.value) &&
      !portsConflict.value &&
      ecValid
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
  <CmkTabs v-model="activeTab">
    <template #tabs>
      <CmkTab id="grpc">{{ _t('GRPC') }}</CmkTab>
      <CmkTab id="http">{{ _t('HTTP') }}</CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent id="grpc">
        <CmkParagraph>{{
          _t('Configure a GRPC-based OTLP receiver that will collect OpenTelemetry data.')
        }}</CmkParagraph>

        <div class="mode-otel-configure-collector__form">
          <CollectorEndpointConfig
            v-if="endpointConfigAllowed"
            v-model:endpoint="grpcEndpoint"
            :show-errors="displayErrors"
            :both-endpoints-empty="bothEndpointsEmpty"
            :port-conflict="portsConflict"
            address-placeholder="0.0.0.0"
            port-placeholder="4317"
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
          />
        </div>
      </CmkTabContent>

      <CmkTabContent id="http">
        <CmkParagraph>{{
          _t('Configure an HTTP-based OTLP receiver that will collect OpenTelemetry data.')
        }}</CmkParagraph>

        <div class="mode-otel-configure-collector__form">
          <CollectorEndpointConfig
            v-if="endpointConfigAllowed"
            v-model:endpoint="httpEndpoint"
            :show-errors="displayErrors"
            :both-endpoints-empty="bothEndpointsEmpty"
            :port-conflict="portsConflict"
            address-placeholder="0.0.0.0"
            port-placeholder="4318"
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
          />
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
</style>
