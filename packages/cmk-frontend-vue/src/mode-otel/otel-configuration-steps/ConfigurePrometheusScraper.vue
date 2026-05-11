<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export interface PrometheusScraperConfig {
  jobName: string
  metricsPath: string
  address: string
  port: number | undefined
  encryption: boolean
}
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import { validateAddress, validatePort } from './validation.ts'

const { _t } = usei18n()

const jobNameId = useId()
const metricsPathId = useId()
const addressId = useId()
const portId = useId()

const config = defineModel<PrometheusScraperConfig>('config', { required: true })

const displayErrors = ref(false)

const jobNameErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!config.value.jobName.trim()) {
    return [_t('Enter a name for your job.')]
  }
  return []
})

const metricsPathErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  if (!config.value.metricsPath.trim()) {
    return [_t('Metrics path is required but not specified.')]
  }
  if (!config.value.metricsPath.startsWith('/')) {
    return [_t("Metrics path must start with a '/'.")]
  }
  return []
})

const addressErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  return validateAddress(config.value.address, _t)
})

const portErrors = computed<string[]>(() => {
  if (!displayErrors.value) {
    return []
  }
  return validatePort(config.value.port, _t)
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
  <div
    class="mode-otel-configure-prometheus-scraper__form"
    role="group"
    :aria-label="_t('Prometheus scraper')"
  >
    <CmkLabel :for="jobNameId">{{ _t('Job name') }} <CmkLabelRequired /></CmkLabel>
    <CmkInput
      :id="jobNameId"
      v-model="config.jobName"
      type="text"
      field-size="MEDIUM"
      :external-errors="jobNameErrors"
      aria-required="true"
    />

    <CmkLabel
      :for="metricsPathId"
      :help="
        _t(
          'The HTTP resource path on which to fetch metrics from targets. Must start with a \'/\'.'
        )
      "
      >{{ _t('Metrics path') }} <CmkLabelRequired
    /></CmkLabel>
    <CmkInput
      :id="metricsPathId"
      v-model="config.metricsPath"
      type="text"
      field-size="MEDIUM"
      placeholder="/metrics"
      :external-errors="metricsPathErrors"
      aria-required="true"
    />

    <CmkLabel
      :for="addressId"
      :help="
        _t(
          'The IP address or host name the OpenTelemetry Collector should listen on. To listen only locally, use \'127.0.0.1\' or \'::1\'. To listen on all interfaces, use \'0.0.0.0\' or \'::\'.'
        )
      "
      >{{ _t('IP address or host name') }} <CmkLabelRequired
    /></CmkLabel>
    <CmkInput
      :id="addressId"
      v-model="config.address"
      type="text"
      field-size="MEDIUM"
      placeholder="0.0.0.0"
      :external-errors="addressErrors"
      aria-required="true"
    />

    <CmkLabel :for="portId">{{ _t('Port') }} <CmkLabelRequired /></CmkLabel>
    <CmkInput
      :id="portId"
      v-model="config.port"
      type="number"
      placeholder="9090"
      :external-errors="portErrors"
      aria-required="true"
    />

    <CmkLabel
      :help="
        _t(
          `Serves the OTLP endpoint over TLS using the site's certificate. The client must trust the site CA at ~/etc/ssl/ca.pem. The certificate's server name matches the site ID.`
        )
      "
      >{{ _t('Encryption') }}</CmkLabel
    >
    <CmkCheckbox v-model="config.encryption" :label="_t('Encrypt communication with TLS')" />
  </div>
</template>

<style scoped>
.mode-otel-configure-prometheus-scraper__form {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;
  margin-top: var(--spacing);
}
</style>
