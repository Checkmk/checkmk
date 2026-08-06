<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import ModesCell from '@/monitoring/shared/components/cell/ModesCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

const props = defineProps<{ row: HostServiceEntry; tableRow: Row<HostServiceEntry> }>()

const { _t } = usei18n()

const emit = defineEmits<{
  (event: 'open', service: HostServiceEntry): void
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

function toggleSelected(selected: boolean): void {
  props.tableRow.toggleSelected(selected)
}

const lastCheck = computed(() =>
  props.row.last_check === null ? '–' : formatTimestamp(props.row.last_check)
)
const lastStateChange = computed(() => formatTimestamp(props.row.last_state_change))
</script>

<template>
  <CheckboxCell
    v-if="hasColumn('select')"
    column-id="select"
    :aria-label="_t('Select service %{name}', { name: row.name })"
    :model-value="tableRow.getIsSelected()"
    @update:model-value="toggleSelected"
  />
  <StateCell v-if="hasColumn('state')" column-id="state" kind="service" :state="row.state" />
  <ModesCell v-if="hasColumn('modes')" column-id="modes" :modes="row.modes ?? []" />
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
