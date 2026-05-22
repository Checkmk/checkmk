<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import ConfigurationSummary, { type SummaryEntry } from './ConfigurationSummary.vue'
import {
  type AuthConfig,
  type EndpointConfig,
  type EventConsoleConfig,
  GRPC_DEFAULT_PORT,
  HTTP_DEFAULT_PORT,
  resolveEndpoint
} from './otelTypes'

const { _t } = usei18n()

const props = defineProps<{
  configName: string
  siteId: string
  grpcEnabled: boolean
  httpEnabled: boolean
  grpcAuth: AuthConfig
  httpAuth: AuthConfig
  grpcEndpoint: EndpointConfig
  httpEndpoint: EndpointConfig
  grpcEncryption: boolean
  httpEncryption: boolean
  grpcEventConsole: EventConsoleConfig | null
  httpEventConsole: EventConsoleConfig | null
  grpcPasswordName: string
  httpPasswordName: string
  endpointConfigAllowed: boolean
  encryptionAllowed: boolean
  eventConsoleAllowed: boolean
}>()

function describeAuth(auth: AuthConfig, passwordName: string): string {
  if (auth.method === 'none') {
    return _t('No authentication')
  }
  const user = auth.credential?.username ?? ''
  return _t('Basic auth (user: %{user}, password title: %{password})', {
    user,
    password: passwordName
  })
}

function formatEndpoint(endpoint: EndpointConfig, defaultPort: number): string | null {
  const resolved = resolveEndpoint(endpoint, defaultPort)
  if (resolved === null) {
    return null
  }
  return `${resolved.address}:${resolved.port}`
}

function buildProtocolEntries(
  sectionTitle: string,
  auth: AuthConfig,
  endpoint: EndpointConfig,
  defaultPort: number,
  encryption: boolean,
  eventConsole: EventConsoleConfig | null,
  passwordName: string
): SummaryEntry[] {
  const entries: SummaryEntry[] = [{ kind: 'section', title: sectionTitle }]
  if (props.endpointConfigAllowed) {
    const formatted = formatEndpoint(endpoint, defaultPort)
    if (formatted !== null) {
      entries.push({ kind: 'row', label: _t('Endpoint'), value: formatted })
    }
  }
  entries.push({
    kind: 'row',
    label: _t('Authentication'),
    value: describeAuth(auth, passwordName)
  })
  if (props.encryptionAllowed) {
    entries.push({
      kind: 'row',
      label: _t('Encryption'),
      value: encryption ? _t('TLS enabled') : _t('No encryption')
    })
  }
  if (props.eventConsoleAllowed && eventConsole !== null) {
    entries.push({
      kind: 'row',
      label: _t('Send log messages to event console'),
      value: _t('Enabled (Resource attribute: %{attribute})', {
        attribute: eventConsole.resourceAttribute
      })
    })
  }
  return entries
}

const footnote = _t('The hosts will be created in the "Telemetry" folder.')

const entries = computed<SummaryEntry[]>(() => {
  const result: SummaryEntry[] = [
    { kind: 'row', label: _t('Configuration name'), value: props.configName },
    { kind: 'row', label: _t('Site'), value: props.siteId }
  ]
  if (props.grpcEnabled) {
    result.push(
      ...buildProtocolEntries(
        _t('gRPC-based OTLP receiver:'),
        props.grpcAuth,
        props.grpcEndpoint,
        GRPC_DEFAULT_PORT,
        props.grpcEncryption,
        props.grpcEventConsole,
        props.grpcPasswordName
      )
    )
  }
  if (props.httpEnabled) {
    result.push(
      ...buildProtocolEntries(
        _t('HTTP-based OTLP receiver:'),
        props.httpAuth,
        props.httpEndpoint,
        HTTP_DEFAULT_PORT,
        props.httpEncryption,
        props.httpEventConsole,
        props.httpPasswordName
      )
    )
  }
  return result
})
</script>

<template>
  <ConfigurationSummary :entries="entries" :footnote="footnote" />
</template>
