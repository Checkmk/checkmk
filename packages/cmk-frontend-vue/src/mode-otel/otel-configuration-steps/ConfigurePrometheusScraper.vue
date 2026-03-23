<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const { _t } = usei18n()

const jobName = defineModel<string>('jobName', { required: true })
const metricsPath = defineModel<string>('metricsPath', { required: true })
const address = defineModel<string>('address', { required: true })
const port = defineModel<number | undefined>('port', { required: true })

const displayErrors = ref(false)

const HOSTNAME_PATTERN =
  /^(?:(?:\d{1,3}\.){3}\d{1,3}|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|::1?|::ffff:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9a-fA-F:]+)$/

const jobNameErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!jobName.value.trim()) {
    return [_t('Enter a name for your job.')]
  }
  return []
})

const metricsPathErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!metricsPath.value.trim()) {
    return [_t('Metrics path is required but not specified.')]
  }
  if (!metricsPath.value.startsWith('/')) {
    return [_t("Metrics path must start with a '/'.")]
  }
  return []
})

const addressErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!address.value.trim()) {
    return [_t('Enter a valid IP address or host name.')]
  }
  if (!HOSTNAME_PATTERN.test(address.value.trim())) {
    return [_t('Your input is not a valid host name or IP address.')]
  }
  return []
})

const portErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (port.value === undefined) {
    return [_t('Enter a valid port number (example: 1234).')]
  }
  if (!Number.isInteger(port.value)) {
    return [_t('Port must be a whole number.')]
  }
  if (port.value < 1 || port.value > 65535) {
    return [_t('Port must be between 1 and 65535.')]
  }
  return []
})

function validate(): boolean {
  displayErrors.value = true
  return (
    jobNameErrors.value.length === 0 &&
    metricsPathErrors.value.length === 0 &&
    addressErrors.value.length === 0 &&
    portErrors.value.length === 0
  )
}

defineExpose({ validate })
</script>

<template>
  <div class="mode-otel-configure-prometheus-scraper__form">
    <CmkLabel>{{ _t('Job name') }} <CmkLabelRequired /></CmkLabel>
    <CmkInput v-model="jobName" type="text" field-size="MEDIUM" :external-errors="jobNameErrors" />

    <CmkLabel
      :help="
        _t(
          'The HTTP resource path on which to fetch metrics from targets. Must start with a \'/\'.'
        )
      "
      >{{ _t('Metrics path') }} <CmkLabelRequired
    /></CmkLabel>
    <CmkInput
      v-model="metricsPath"
      type="text"
      field-size="MEDIUM"
      placeholder="/metrics"
      :external-errors="metricsPathErrors"
    />

    <CmkLabel
      :help="
        _t(
          'The IP address or host name the OpenTelemetry Collector should listen on. To listen only locally, use \'127.0.0.1\' or \'::1\'. To listen on all interfaces, use \'0.0.0.0\' or \'::\'.'
        )
      "
      >{{ _t('IP address or hostname') }} <CmkLabelRequired
    /></CmkLabel>
    <CmkInput
      v-model="address"
      type="text"
      field-size="MEDIUM"
      placeholder="0.0.0.0"
      :external-errors="addressErrors"
    />

    <CmkLabel>{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
    <CmkInput v-model="port" type="number" placeholder="0" :external-errors="portErrors" />
  </div>
</template>

<style scoped>
.mode-otel-configure-prometheus-scraper__form {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;
}
</style>
