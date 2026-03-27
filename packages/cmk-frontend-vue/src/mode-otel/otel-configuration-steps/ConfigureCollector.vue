<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export type AuthMethod = 'none' | 'basicauth'

export interface Credential {
  username: string
  password: string // password store ID
}

export interface AuthConfig {
  method: AuthMethod
  credential: Credential | null
}

export interface EndpointConfig {
  address: string
  port: number | undefined
}

export interface EventConsoleConfig {
  resourceAttribute: string
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import PasswordStoreSlideIn from './PasswordStoreSlideIn.vue'
import type { PasswordConfig } from './password_store_password.types.ts'

const { _t } = usei18n()

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

const activeTab = ref('grpc')
const availablePasswords = ref<Suggestion[]>([])
const displayErrors = ref(false)
const passwordStoreSlideInOpen = ref(false)

onMounted(async () => {
  try {
    const response = await fetchRestAPI(
      'api/v1/domain-types/passwordstore_password/collections/passwordstore_password',
      'GET'
    )
    const data = await response.json()
    availablePasswords.value = data.value.map((p: { id: string; title: string }) => ({
      name: p.id,
      title: p.title
    }))
  } catch {
    // password store unavailable — leave list empty
  }
})

const authMethodOptions = computed<Suggestion[]>(() => {
  if (!props.noAuthAllowed) {
    return [{ name: 'basicauth', title: _t('Basic authentication') }]
  }
  return [
    { name: 'none', title: _t('No authentication') },
    { name: 'basicauth', title: _t('Basic authentication') }
  ]
})

watch(
  () => grpcAuth.value.method,
  (method) => {
    if (method === 'basicauth' && grpcAuth.value.credential === null) {
      grpcAuth.value.credential = { username: '', password: '' }
    }
  },
  { immediate: true }
)

watch(
  () => httpAuth.value.method,
  (method) => {
    if (method === 'basicauth' && httpAuth.value.credential === null) {
      httpAuth.value.credential = { username: '', password: '' }
    }
  },
  { immediate: true }
)

function credentialUsernameErrors(credential: Credential): string[] {
  if (!displayErrors.value) {
    return []
  }
  if (!credential.username.trim()) {
    return [_t('Username is required but not specified.')]
  }
  return []
}

function credentialPasswordErrors(credential: Credential): string[] {
  if (!displayErrors.value) {
    return []
  }
  if (!credential.password) {
    return [_t('Password is required but not specified.')]
  }
  return []
}

const grpcUsernameErrors = computed(() =>
  grpcAuth.value.credential ? credentialUsernameErrors(grpcAuth.value.credential) : []
)
const grpcPasswordErrors = computed(() =>
  grpcAuth.value.credential ? credentialPasswordErrors(grpcAuth.value.credential) : []
)
const httpUsernameErrors = computed(() =>
  httpAuth.value.credential ? credentialUsernameErrors(httpAuth.value.credential) : []
)
const httpPasswordErrors = computed(() =>
  httpAuth.value.credential ? credentialPasswordErrors(httpAuth.value.credential) : []
)

const grpcEventConsoleErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (grpcEventConsole.value !== null && !grpcEventConsole.value.resourceAttribute.trim()) {
    return [
      _t(
        'You must set a resource attribute (e.g., service.name) so the system can determine the host name.'
      )
    ]
  }
  return []
})
const httpEventConsoleErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (httpEventConsole.value !== null && !httpEventConsole.value.resourceAttribute.trim()) {
    return [
      _t(
        'You must set a resource attribute (e.g., service.name) so the system can determine the host name.'
      )
    ]
  }
  return []
})

const bothEndpointsEmpty = computed(
  () => !grpcEndpoint.value.address.trim() && !httpEndpoint.value.address.trim()
)

const grpcAddressErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (!grpcEndpoint.value.address.trim()) {
    return bothEndpointsEmpty.value ? [_t('Enter a valid IP address or host name.')] : []
  }
  return validateAddress(grpcEndpoint.value.address)
})
const grpcPortErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (grpcEndpoint.value.port !== undefined || grpcEndpoint.value.address.trim()) {
    return validatePort(grpcEndpoint.value.port)
  }
  return []
})
const httpAddressErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (!httpEndpoint.value.address.trim()) {
    return bothEndpointsEmpty.value ? [_t('Enter a valid IP address or host name.')] : []
  }
  return validateAddress(httpEndpoint.value.address)
})
const httpPortErrors = computed((): string[] => {
  if (!displayErrors.value) {
    return []
  }
  if (httpEndpoint.value.port !== undefined || httpEndpoint.value.address.trim()) {
    return validatePort(httpEndpoint.value.port)
  }
  return []
})

function tabHasErrors(auth: AuthConfig): boolean {
  if (auth.method !== 'basicauth') {
    return false
  }
  return !auth.credential?.username.trim() || !auth.credential?.password
}

function isValidIpOrHostname(value: string): boolean {
  const ipv4Match = value.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
  if (ipv4Match) {
    return ipv4Match.slice(1).every((p) => parseInt(p, 10) <= 255)
  }
  if (value.includes(':')) {
    return /^[0-9a-fA-F:]+$/.test(value) && value.split(':').length >= 2
  }
  const h = value.endsWith('.') ? value.slice(0, -1) : value
  if (!h || h.length > 253) {
    return false
  }
  const labels = h.split('.')
  if (/^\d+$/.test(labels[labels.length - 1] ?? '')) {
    return false
  }
  return labels.every((l) => l.length > 0 && /^(?!-)[a-z0-9-]{1,63}(?<!-)$/i.test(l))
}

const validateAddress = (value: string): string[] => {
  if (!value.trim()) {
    return [_t('Enter a valid IP address or host name.')]
  }
  if (!isValidIpOrHostname(value)) {
    return [_t('Your input is not a valid host name or IP address.')]
  }
  return []
}

const validatePort = (value: number | undefined): string[] => {
  if (value === undefined || value < 1 || value > 65535) {
    return [_t('Enter a valid port number (example: 1234).')]
  }
  return []
}

function endpointIsConfigured(endpoint: EndpointConfig): boolean {
  return !!endpoint.address.trim()
}

function configuredEndpointHasErrors(endpoint: EndpointConfig): boolean {
  return !isValidIpOrHostname(endpoint.address) || validatePort(endpoint.port).length > 0
}

function tabHasValidationErrors(tab: 'grpc' | 'http'): boolean {
  const authErrors = tab === 'grpc' ? tabHasErrors(grpcAuth.value) : tabHasErrors(httpAuth.value)
  const ecErrors =
    tab === 'grpc'
      ? grpcEventConsoleErrors.value.length > 0
      : httpEventConsoleErrors.value.length > 0
  if (!props.endpointConfigAllowed) {
    return authErrors || ecErrors
  }
  const addrErrors =
    tab === 'grpc' ? grpcAddressErrors.value.length > 0 : httpAddressErrors.value.length > 0
  const portErrors =
    tab === 'grpc' ? grpcPortErrors.value.length > 0 : httpPortErrors.value.length > 0
  return authErrors || ecErrors || addrErrors || portErrors
}

function validate(): boolean {
  displayErrors.value = true
  const eventConsoleValid =
    grpcEventConsoleErrors.value.length === 0 && httpEventConsoleErrors.value.length === 0

  let isValid: boolean
  if (!props.endpointConfigAllowed) {
    isValid = !tabHasErrors(grpcAuth.value) && !tabHasErrors(httpAuth.value) && eventConsoleValid
  } else {
    const grpcConfigured = endpointIsConfigured(grpcEndpoint.value)
    const httpConfigured = endpointIsConfigured(httpEndpoint.value)
    if (!grpcConfigured && !httpConfigured) {
      isValid = false
    } else {
      const grpcValid = !grpcConfigured || !configuredEndpointHasErrors(grpcEndpoint.value)
      const httpValid = !httpConfigured || !configuredEndpointHasErrors(httpEndpoint.value)
      isValid =
        !tabHasErrors(grpcAuth.value) &&
        !tabHasErrors(httpAuth.value) &&
        grpcValid &&
        httpValid &&
        eventConsoleValid
    }
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

function onPasswordCreated(password: PasswordConfig) {
  passwordStoreSlideInOpen.value = false
  // TODO: properly handle the created password
  availablePasswords.value.push({
    name: password.general_props.id,
    title: password.general_props.title as TranslatedString
  })
}

defineExpose({ validate })
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
          <template v-if="endpointConfigAllowed">
            <CmkLabel>{{ _t('IP address or host name') }} <CmkLabelRequired /></CmkLabel>
            <CmkInput
              v-model="grpcEndpoint.address"
              type="text"
              field-size="MEDIUM"
              :placeholder="_t('0.0.0.0')"
              :external-errors="grpcAddressErrors"
            />
            <CmkLabel>{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
            <CmkInput
              v-model="grpcEndpoint.port"
              type="number"
              :external-errors="grpcPortErrors"
              :placeholder="_t('4317')"
            />
          </template>

          <CmkLabel>{{ _t('Authentication method') }}</CmkLabel>
          <CmkDropdown
            v-model:selected-option="grpcAuth.method"
            :options="{ type: 'fixed', suggestions: authMethodOptions }"
            :label="_t('Authentication method')"
          />

          <template v-if="grpcAuth.method === 'basicauth' && grpcAuth.credential !== null">
            <span />
            <div class="mode-otel-configure-collector__sub-field">
              <CmkLabel>{{ _t('Username') }} <CmkLabelRequired /></CmkLabel>
              <CmkInput
                v-model="grpcAuth.credential.username"
                type="text"
                field-size="MEDIUM"
                :placeholder="_t('Username')"
                :external-errors="grpcUsernameErrors"
              />

              <CmkLabel>{{ _t('Password') }} <CmkLabelRequired /></CmkLabel>
              <div class="mode-otel-configure-collector__password-row">
                <CmkDropdown
                  v-model:selected-option="grpcAuth.credential.password"
                  :options="{ type: 'fixed', suggestions: availablePasswords }"
                  :input-hint="_t('Select password')"
                  :label="_t('Password')"
                  :form-validation="grpcPasswordErrors.length > 0"
                  :no-elements-text="_t('No passwords available')"
                />
                <CmkInlineButton @click="passwordStoreSlideInOpen = true">{{
                  _t('Create')
                }}</CmkInlineButton>
              </div>
              <CmkInlineValidation
                v-if="grpcPasswordErrors.length"
                class="mode-otel-configure-collector__password-error"
                :validation="grpcPasswordErrors"
              />
            </div>
          </template>

          <template v-if="encryptionAllowed">
            <CmkLabel>{{ _t('Encryption') }}</CmkLabel>
            <CmkCheckbox v-model="grpcEncryption" :label="_t('Encrypt communication with TLS')" />
          </template>

          <template v-if="eventConsoleAllowed">
            <CmkLabel>{{ _t('Event Console') }}</CmkLabel>
            <CmkCheckbox
              :model-value="grpcEventConsole !== null"
              :label="_t('Send log messages to event console')"
              @update:model-value="grpcEventConsole = $event ? { resourceAttribute: '' } : null"
            />
            <template v-if="grpcEventConsole !== null">
              <span />
              <div class="mode-otel-configure-collector__sub-field">
                <CmkLabel
                  >{{ _t('Resource attribute for host name lookup') }} <CmkLabelRequired
                /></CmkLabel>
                <CmkInput
                  v-model="grpcEventConsole.resourceAttribute"
                  type="text"
                  field-size="MEDIUM"
                  :placeholder="_t('service.name')"
                  :external-errors="grpcEventConsoleErrors"
                />
              </div>
            </template>
          </template>
        </div>
      </CmkTabContent>

      <CmkTabContent id="http">
        <CmkParagraph>{{
          _t('Configure an HTTP-based OTLP receiver that will collect OpenTelemetry data.')
        }}</CmkParagraph>

        <div class="mode-otel-configure-collector__form">
          <template v-if="endpointConfigAllowed">
            <CmkLabel>{{ _t('IP address or host name') }} <CmkLabelRequired /></CmkLabel>
            <CmkInput
              v-model="httpEndpoint.address"
              type="text"
              field-size="MEDIUM"
              :placeholder="_t('0.0.0.0')"
              :external-errors="httpAddressErrors"
            />
            <CmkLabel>{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
            <CmkInput
              v-model="httpEndpoint.port"
              type="number"
              :external-errors="httpPortErrors"
              :placeholder="_t('4318')"
            />
          </template>

          <CmkLabel>{{ _t('Authentication method') }}</CmkLabel>
          <CmkDropdown
            v-model:selected-option="httpAuth.method"
            :options="{ type: 'fixed', suggestions: authMethodOptions }"
            :label="_t('Authentication method')"
          />

          <template v-if="httpAuth.method === 'basicauth' && httpAuth.credential !== null">
            <span />
            <div class="mode-otel-configure-collector__sub-field">
              <CmkLabel>{{ _t('Username') }} <CmkLabelRequired /></CmkLabel>
              <CmkInput
                v-model="httpAuth.credential.username"
                type="text"
                field-size="MEDIUM"
                :placeholder="_t('Username')"
                :external-errors="httpUsernameErrors"
              />

              <CmkLabel>{{ _t('Password') }} <CmkLabelRequired /></CmkLabel>
              <div class="mode-otel-configure-collector__password-row">
                <CmkDropdown
                  v-model:selected-option="httpAuth.credential.password"
                  :options="{ type: 'fixed', suggestions: availablePasswords }"
                  :input-hint="_t('Select password')"
                  :label="_t('Password')"
                  :form-validation="httpPasswordErrors.length > 0"
                  :no-elements-text="_t('No passwords available')"
                />
                <CmkInlineButton @click="passwordStoreSlideInOpen = true">{{
                  _t('Create')
                }}</CmkInlineButton>
              </div>
              <CmkInlineValidation
                v-if="httpPasswordErrors.length"
                class="mode-otel-configure-collector__password-error"
                :validation="httpPasswordErrors"
              />
            </div>
          </template>

          <template v-if="encryptionAllowed">
            <CmkLabel>{{ _t('Encryption') }}</CmkLabel>
            <CmkCheckbox v-model="httpEncryption" :label="_t('Encrypt communication with TLS')" />
          </template>

          <template v-if="eventConsoleAllowed">
            <CmkLabel>{{ _t('Event Console') }}</CmkLabel>
            <CmkCheckbox
              :model-value="httpEventConsole !== null"
              :label="_t('Send log messages to event console')"
              @update:model-value="httpEventConsole = $event ? { resourceAttribute: '' } : null"
            />
            <template v-if="httpEventConsole !== null">
              <span />
              <div class="mode-otel-configure-collector__sub-field">
                <CmkLabel
                  >{{ _t('Resource attribute for host name lookup') }} <CmkLabelRequired
                /></CmkLabel>
                <CmkInput
                  v-model="httpEventConsole.resourceAttribute"
                  type="text"
                  field-size="MEDIUM"
                  :placeholder="_t('service.name')"
                  :external-errors="httpEventConsoleErrors"
                />
              </div>
            </template>
          </template>
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

.mode-otel-configure-collector__password-row {
  display: flex;
  gap: var(--spacing);
  align-items: center;
}

.mode-otel-configure-collector__password-error {
  grid-column: 2;
}

.mode-otel-configure-collector__sub-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing) var(--dimension-6);
  margin-left: var(--spacing);
  border-left: var(--button-form-border-color) 1px solid;
  padding-left: var(--spacing);
}
</style>
