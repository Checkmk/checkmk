<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject } from 'vue'

import { AI_EXPLAIN_ACTION_ID } from '@/monitoring/host-services/aiExplain'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'
import LabelCell from '@/monitoring/shared/components/cell/LabelCell.vue'
import PerfometerCell from '@/monitoring/shared/components/cell/PerfometerCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { MODE_COLUMN_ID, MODE_ICONS_PER_ROW } from '@/monitoring/shared/components/modeColumn'
import { formatDisplayTimestamp } from '@/monitoring/shared/formatTimestamp'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'
import type { DisplayOptions } from '@/monitoring/shared/types'

const props = withDefaults(
  defineProps<{
    row: HostServiceEntry
    tableRow: Row<HostServiceEntry>
    // Always-visible inline buttons; their url may contain a {service} placeholder resolved per row.
    rowActions?: CellAction[]
    /** Whether the user may reschedule at all; what a reschedule does is per service. */
    mayReschedule?: boolean
    /** Lazy loader for the entries of this service's action menu. */
    loadActionMenu?: ((service: string) => Promise<CellAction[]>) | undefined
    displayOptions: DisplayOptions
    aiExplain?: boolean
  }>(),
  { rowActions: () => [], mayReschedule: false, loadActionMenu: undefined, aiExplain: false }
)

const { _t } = usei18n()

const emit = defineEmits<{
  (event: 'open', service: HostServiceEntry): void
  (event: 'openGraphs', service: HostServiceEntry): void
  (event: 'command', payload: { id: string; target: string }): void
  (event: 'explain', service: HostServiceEntry): void
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

function toggleSelected(selected: boolean): void {
  props.tableRow.toggleSelected(selected)
}

const actionButtons = computed<CellAction[]>(() => [
  ...props.rowActions.map((action) => ({
    ...action,
    url: action.url?.replace('{service}', encodeURIComponent(props.row.name))
  })),
  ...(props.aiExplain
    ? [{ id: AI_EXPLAIN_ACTION_ID, label: _t('Explain with AI'), icon: 'sparkle' as const }]
    : [])
])

function onActionSelect(action: CellAction): void {
  if (action.id === AI_EXPLAIN_ACTION_ID) {
    emit('explain', props.row)
    return
  }
  // A service whose check is a byproduct of the agent-based check has nothing of its own to run,
  // so its reschedule targets the service that fetches the data - see the backend's offer.
  const target = action.id === RESCHEDULE_ACTION_ID ? props.row.reschedule?.target : props.row.name
  emit('command', { id: action.id, target: target ?? props.row.name })
}

// A blocked offer carries no target: the entry is shown, greyed out, with the refusal as its
// tooltip. No offer at all means the service cannot be rescheduled and says nothing about it.
const rescheduleAction = computed<CellAction | null>(() => {
  const offer = props.row.reschedule
  if (!props.mayReschedule || offer === undefined) {
    return null
  }
  return {
    id: RESCHEDULE_ACTION_ID,
    label: offer.label as TranslatedString,
    tooltip: offer.tooltip as TranslatedString,
    icon: offer.icon_name as SimpleIcons,
    disabled: offer.target === undefined
  }
})

const actionMenuLoader = computed<(() => Promise<CellAction[]>) | undefined>(() => {
  const load = props.loadActionMenu
  if (load === undefined && rescheduleAction.value === null) {
    return undefined
  }
  return async () => {
    const items = load === undefined ? [] : await load(props.row.name)
    return rescheduleAction.value === null ? items : [rescheduleAction.value, ...items]
  }
})

const lastCheck = computed(() =>
  props.row.last_check === null
    ? '–'
    : formatDisplayTimestamp(props.row.last_check, props.displayOptions)
)
const lastStateChange = computed(() =>
  formatDisplayTimestamp(props.row.last_state_change, props.displayOptions)
)
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
  <StateCell
    v-if="hasColumn('state')"
    column-id="state"
    kind="service"
    :state="row.state"
    :flapping="row.is_flapping"
    :stale="row.stale"
  />
  <IconCell
    v-if="hasColumn(MODE_COLUMN_ID)"
    :column-id="MODE_COLUMN_ID"
    :icons="row.modes ?? []"
    :max-per-row="MODE_ICONS_PER_ROW"
  />
  <StringCell
    v-if="hasColumn('name')"
    column-id="name"
    :value="row.name"
    :button="true"
    @click="emit('open', row)"
  />
  <StringCell v-if="hasColumn('summary')" column-id="summary" :value="row.summary" state-markers />
  <StringCell
    v-if="hasColumn('last_state_change')"
    column-id="last_state_change"
    :value="lastStateChange"
  />
  <StringCell v-if="hasColumn('last_check')" column-id="last_check" :value="lastCheck" />
  <LabelCell v-if="hasColumn('labels')" column-id="labels" :items="labels" size="small" />
  <LabelCell v-if="hasColumn('tags')" column-id="tags" :items="tags" size="small" />
  <LabelCell v-if="hasColumn('contacts')" column-id="contacts" :items="contacts" size="small" />
  <LabelCell
    v-if="hasColumn('contact_groups')"
    column-id="contact_groups"
    :items="contactGroups"
    size="small"
  />
  <PerfometerCell
    v-if="hasColumn('perfometer')"
    column-id="perfometer"
    :data="row.perfometer"
    :button="row.perfometer !== undefined"
    @click="emit('openGraphs', row)"
  />
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
