<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import ConfigurationSummary, { type SummaryEntry } from './ConfigurationSummary.vue'

const { _t } = usei18n()

const props = defineProps<{
  configName: string
  siteId: string
  jobName: string
  metricsPath: string
  address: string
  port: number
  encryption: boolean
}>()

const footnote = _t('The hosts will be created in the "Telemetry" folder.')

const entries = computed<SummaryEntry[]>(() => [
  { kind: 'row', label: _t('Configuration name'), value: props.configName },
  { kind: 'row', label: _t('Site'), value: props.siteId },
  { kind: 'row', label: _t('Job name'), value: props.jobName },
  { kind: 'row', label: _t('Metrics path'), value: props.metricsPath },
  { kind: 'row', label: _t('IP address or host name'), value: props.address },
  { kind: 'row', label: _t('Port'), value: String(props.port) },
  {
    kind: 'row',
    label: _t('Encryption'),
    value: props.encryption ? _t('TLS enabled') : _t('No encryption')
  }
])
</script>

<template>
  <ConfigurationSummary :entries="entries" :footnote="footnote" />
</template>
