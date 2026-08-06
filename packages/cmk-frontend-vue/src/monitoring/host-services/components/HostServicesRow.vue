<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

const props = defineProps<{ row: HostServiceEntry }>()

const emit = defineEmits<{
  (event: 'open', service: HostServiceEntry): void
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

const lastCheck = computed(() => formatTimestamp(props.row.last_check))
const lastStateChange = computed(() => formatTimestamp(props.row.last_state_change))
</script>

<template>
  <StateCell v-if="hasColumn('state')" column-id="state" kind="service" :state="row.state" />
  <StringCell
    v-if="hasColumn('name')"
    column-id="name"
    :value="row.name"
    :button="true"
    @click="emit('open', row)"
  />
  <StringCell v-if="hasColumn('summary')" column-id="summary" :value="row.summary" />
  <StringCell v-if="hasColumn('last_check')" column-id="last_check" :value="lastCheck" />
  <StringCell
    v-if="hasColumn('last_state_change')"
    column-id="last_state_change"
    :value="lastStateChange"
  />
</template>
