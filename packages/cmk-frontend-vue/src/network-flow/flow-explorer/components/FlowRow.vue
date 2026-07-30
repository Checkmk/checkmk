<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'

import { formatBytes, formatCount, formatTimeOfDay } from '../../format'
import type { FlowEntry } from '../api/flows'
import FlowEndpointCell from './FlowEndpointCell.vue'

const props = defineProps<{ row: FlowEntry }>()

const { _t } = usei18n()

const DIRECTION_TITLES: Record<FlowEntry['direction'], string> = {
  ingress: _t('Ingress'),
  egress: _t('Egress'),
  internal: _t('Internal'),
  external: _t('External')
}

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

// ifIndex 0 is the flow's "not reported", not interface number zero.
function interfaceLabel(ifIndex: number): string | undefined {
  return ifIndex === 0 ? undefined : String(ifIndex)
}

const direction = computed(() => DIRECTION_TITLES[props.row.direction])
</script>

<template>
  <StringCell
    v-if="hasColumn('first_seen')"
    column-id="first_seen"
    :value="formatTimeOfDay(row.first_seen)"
    no-wrap
  />
  <FlowEndpointCell
    v-if="hasColumn('source_ip')"
    column-id="source_ip"
    :address="row.source_ip"
    :port="row.source_port"
    :asn="row.source_asn"
  />
  <FlowEndpointCell
    v-if="hasColumn('destination_ip')"
    column-id="destination_ip"
    :address="row.destination_ip"
    :port="row.destination_port"
    :asn="row.destination_asn"
  />
  <StringCell
    v-if="hasColumn('protocol_name')"
    column-id="protocol_name"
    :value="row.protocol_name"
    no-wrap
  />
  <StringCell v-if="hasColumn('application')" column-id="application" :value="row.application" />
  <!-- Bytes and packets are SI-formatted strings rather than NumberCell values,
       which would render 1.92 GB as 1920000000. -->
  <StringCell
    v-if="hasColumn('total_bytes')"
    column-id="total_bytes"
    :value="formatBytes(row.total_bytes)"
    no-wrap
  />
  <StringCell
    v-if="hasColumn('packets')"
    column-id="packets"
    :value="formatCount(row.packets)"
    no-wrap
  />
  <StringCell v-if="hasColumn('direction')" column-id="direction" :value="direction" no-wrap />
  <StringCell
    v-if="hasColumn('input_interface')"
    column-id="input_interface"
    :value="interfaceLabel(row.input_interface)"
    no-wrap
  />
  <StringCell
    v-if="hasColumn('output_interface')"
    column-id="output_interface"
    :value="interfaceLabel(row.output_interface)"
    no-wrap
  />
  <StringCell
    v-if="hasColumn('last_seen')"
    column-id="last_seen"
    :value="formatTimeOfDay(row.last_seen)"
    no-wrap
  />
</template>
