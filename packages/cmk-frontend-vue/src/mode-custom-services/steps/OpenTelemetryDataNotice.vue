<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { HostOpenTelemetryData } from '../definition'
import type { OpenTelemetryData } from '../openTelemetryData'

const { _t } = usei18n()

const { data } = defineProps<{ data: OpenTelemetryData }>()

const hosts = computed<HostOpenTelemetryData[]>(() => (data.status === 'loaded' ? data.hosts : []))

const hostsToEnable = computed(() =>
  hosts.value
    .filter((host) => host.opentelemetry_data === 'to_enable')
    .map((host) => host.host_name)
)

const lockedHosts = computed(() =>
  hosts.value.filter((host) => host.opentelemetry_data === 'locked')
)

function lockedWarning({ host_name: host, dcd_connection: connection }: HostOpenTelemetryData) {
  return connection
    ? _t(
        'OpenTelemetry data is disabled on %{host} by the dynamic host management connection "%{connection}", so this service will not receive data on that host. Enable OpenTelemetry data in that connection.',
        { host, connection: connection.title }
      )
    : _t(
        'OpenTelemetry data is disabled and locked on %{host}, so this service will not receive data on that host.',
        { host }
      )
}
</script>

<template>
  <CmkAlert
    v-if="hostsToEnable.length > 0"
    size="small"
    variant="info"
    :text="
      _t('OpenTelemetry data will be enabled on %{hosts} when you save.', {
        hosts: hostsToEnable.join(', ')
      })
    "
  />
  <CmkAlert
    v-for="host in lockedHosts"
    :key="host.host_name"
    size="small"
    variant="warning"
    :text="lockedWarning(host)"
  />
  <CmkAlert
    v-if="data.status === 'failed'"
    size="small"
    variant="warning"
    :text="_t('Could not check whether OpenTelemetry data is enabled on the hosts.')"
  />
</template>
