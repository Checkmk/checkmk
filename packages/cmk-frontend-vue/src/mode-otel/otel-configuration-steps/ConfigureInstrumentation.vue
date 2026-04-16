<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCode from '@/components/CmkCode.vue'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import { type CollectorSnippetInput, buildCollectorSnippets } from './otelSnippets'
import type { AuthConfig, EndpointConfig } from './otelTypes'

const { _t } = usei18n()

const props = defineProps<{
  siteName: string
  httpEndpoint: EndpointConfig
  grpcEndpoint: EndpointConfig
  httpTlsEnabled: boolean
  grpcTlsEnabled: boolean
  grpcAuth: AuthConfig
  httpAuth: AuthConfig
  sendLogsToEc: boolean
}>()

const activeTab = ref('collector')

const snippetInput = computed<CollectorSnippetInput>(() => ({
  siteName: props.siteName,
  httpInfo: {
    endpoint: props.httpEndpoint,
    tlsEnabled: props.httpTlsEnabled,
    auth: props.httpAuth
  },
  grpcInfo: {
    endpoint: props.grpcEndpoint,
    tlsEnabled: props.grpcTlsEnabled,
    auth: props.grpcAuth
  },
  sendLogsToEc: props.sendLogsToEc
}))

const snippets = computed(() => buildCollectorSnippets(snippetInput.value))

const basicAuthEnabled = computed(
  () => props.httpAuth.method === 'basicauth' || props.grpcAuth.method === 'basicauth'
)

const sdkEndpointDisplay = computed(() => {
  const endpoint =
    props.httpEndpoint.address || props.httpEndpoint.port !== undefined
      ? props.httpEndpoint
      : props.grpcEndpoint
  const address = endpoint.address || '<host>'
  const port = endpoint.port ?? 4318
  return `${address}:${port}`
})

const sdkAuthExample = 'echo -n "username:password" | base64'
const sdkAuthHeaderExample = 'Authorization: Basic YWRtaW46c2VjcmV0'
</script>

<template>
  <CmkParagraph>
    {{
      _t('OpenTelemetry instrumentation can be set up in two ways, depending on your environment:')
    }}
  </CmkParagraph>
  <ul>
    <li>
      <strong>{{ _t('OpenTelemetry Collector') }}</strong> —
      {{
        _t(
          'A vendor-agnostic proxy service that receives, processes, and forwards telemetry data. Use this when you want a centralised point to collect data from multiple sources before forwarding it to Checkmk.'
        )
      }}
    </li>
    <li>
      <strong>{{ _t('SDKs (Software Development Kits)') }}</strong> —
      {{
        _t(
          'Language-specific libraries (e.g. for Python, Java, Go) that you integrate directly into your application code to generate and export telemetry data. Use this when you want to instrument your application directly without an intermediary.'
        )
      }}
    </li>
  </ul>
  <CmkParagraph>
    {{
      _t(
        'Both options are supported. This step provides a ready-to-use configuration snippet for each, pre-filled with the correct IP address and port for your environment.'
      )
    }}
    <br />
  </CmkParagraph>

  <CmkTabs v-model="activeTab" class="mode-otel-configure-instrumentation__tabs">
    <template #tabs>
      <CmkTab id="collector">{{ _t('OpenTelemetry Collector') }}</CmkTab>
      <CmkTab id="sdk">{{ _t('SDKs') }}</CmkTab>
    </template>

    <template #tab-contents>
      <CmkTabContent id="collector">
        <CmkHeading type="h4">
          {{ _t('Configuration for OpenTelemetry Collector') }}
        </CmkHeading>
        <CmkParagraph>
          {{
            _t(
              "The configuration snippets provided for the OpenTelemetry Collector option can be copied directly into your Collector's configuration file (typically config.yaml)."
            )
          }}
        </CmkParagraph>
        <br />
        <CmkCode
          :title="_t('Exporters configuration')"
          :code_txt="snippets.exporters"
          width="fill"
        />
        <CmkCode
          v-if="snippets.extensions"
          :title="_t('Extension configuration')"
          :code_txt="snippets.extensions"
          width="fill"
        />
        <CmkCode :title="_t('Service configuration')" :code_txt="snippets.service" width="fill" />
      </CmkTabContent>

      <CmkTabContent id="sdk">
        <CmkHeading type="h4">{{ _t('Configuration for SDKs') }}</CmkHeading>
        <CmkParagraph>
          {{ _t('Update your settings directly in your code.') }}
        </CmkParagraph>
        <ul>
          <li>
            <strong>{{ _t('Endpoint') }}:</strong> {{ sdkEndpointDisplay }}
          </li>
          <li v-if="basicAuthEnabled">
            <strong>{{ _t('Headers') }}:</strong>
            {{ _t('Set Authorization to "Basic {base64-encoded-credentials}"') }}
          </li>
        </ul>
        <CmkParagraph>
          <em>{{ _t('Note: The exact syntax depends on the language SDK.') }}</em>
        </CmkParagraph>
        <br />

        <template v-if="basicAuthEnabled">
          <CmkHeading type="h4">
            {{ _t('How to generate your Authorization header?') }}
          </CmkHeading>
          <CmkParagraph>
            {{
              _t(
                'The Basic auth format requires a Base64-encoded string of your username:password.'
              )
            }}
          </CmkParagraph>
          <br />
          <CmkParagraph>
            {{
              _t(
                'To generate this string, open a terminal and run the following command (replace the placeholders with your actual Checkmk credentials):'
              )
            }}
          </CmkParagraph>
          <div class="mode-otel-configure-instrumentation__code-text">
            {{ sdkAuthExample }}
          </div>
          <br />
          <CmkHeading type="h4">
            {{ _t('Example:') }}
          </CmkHeading>
          <CmkParagraph>
            {{
              _t(
                'if your username is "admin" and password is "secret", the command output would be YWRtaW46c2VjcmV0. Your header would then look like:'
              )
            }}
          </CmkParagraph>
          <div class="mode-otel-configure-instrumentation__code-text">
            {{ sdkAuthHeaderExample }}
          </div>
        </template>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>

<style scoped>
.mode-otel-configure-instrumentation__tabs {
  margin-top: var(--spacing);
}

.mode-otel-configure-instrumentation__code-text {
  font-family: monospace;
  font-size: var(--font-size-normal, 12px);
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}
</style>
