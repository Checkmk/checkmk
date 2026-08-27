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
import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'
import LabelCell from '@/monitoring/shared/components/cell/LabelCell.vue'
import PerfometerCell from '@/monitoring/shared/components/cell/PerfometerCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'

const props = withDefaults(
  defineProps<{
    row: HostServiceEntry
    tableRow: Row<HostServiceEntry>
    // Always-visible inline buttons; their url may contain a {service} placeholder resolved per row.
    rowActions?: CellAction[]
    /** Lazy loader for the entries of this service's action menu. */
    loadActionMenu?: ((service: string) => Promise<CellAction[]>) | undefined
  }>(),
  { rowActions: () => [], loadActionMenu: undefined }
)

const { _t } = usei18n()

const emit = defineEmits<{
  (event: 'open', service: HostServiceEntry): void
  (event: 'command', payload: { id: string; target: string }): void
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

function toggleSelected(selected: boolean): void {
  props.tableRow.toggleSelected(selected)
}

const actionButtons = computed<CellAction[]>(() =>
  props.rowActions.map((action) => ({
    ...action,
    url: action.url?.replace('{service}', encodeURIComponent(props.row.name))
  }))
)

function onActionSelect(action: CellAction): void {
  emit('command', { id: action.id, target: props.row.name })
}

const actionMenuLoader = computed<(() => Promise<CellAction[]>) | undefined>(() => {
  const load = props.loadActionMenu
  return load === undefined ? undefined : () => load(props.row.name)
})

const lastCheck = computed(() =>
  props.row.last_check === null ? '–' : formatTimestamp(props.row.last_check)
)
const lastStateChange = computed(() => formatTimestamp(props.row.last_state_change))
const labels = computed(() => toLabelItems(props.row.labels ?? {}))
const tags = computed(() => toTagItems(props.row.tags ?? {}))
const contacts = computed(() => toNameItems(props.row.contacts ?? []))
const contactGroups = computed(() => toNameItems(props.row.contact_groups ?? []))
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
  <IconCell v-if="hasColumn('modes')" column-id="modes" :icons="row.modes ?? []" />
  <StringCell
    v-if="hasColumn('name')"
    column-id="name"
    :value="row.name"
    :button="true"
    @click="emit('open', row)"
  />
  <StringCell v-if="hasColumn('summary')" column-id="summary" :value="row.summary" state-markers />
  <StringCell v-if="hasColumn('last_check')" column-id="last_check" :value="lastCheck" />
  <StringCell
    v-if="hasColumn('last_state_change')"
    column-id="last_state_change"
    :value="lastStateChange"
  />
  <LabelCell v-if="hasColumn('labels')" column-id="labels" :items="labels" size="small" />
  <LabelCell v-if="hasColumn('tags')" column-id="tags" :items="tags" size="small" />
  <LabelCell v-if="hasColumn('contacts')" column-id="contacts" :items="contacts" size="small" />
  <LabelCell
    v-if="hasColumn('contact_groups')"
    column-id="contact_groups"
    :items="contactGroups"
    size="small"
  />
  <PerfometerCell v-if="hasColumn('perfometer')" column-id="perfometer" :data="row.perfometer" />
  <ActionsCell
    v-if="(actionMenuLoader || actionButtons.length > 0) && hasColumn('actions')"
    column-id="actions"
    :actions="actionButtons"
    :max-visible="actionButtons.length"
    :load="actionMenuLoader"
    @select="onActionSelect"
  />
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-base-cell {
  color: var(--font-color-secondary);
}
</style>
