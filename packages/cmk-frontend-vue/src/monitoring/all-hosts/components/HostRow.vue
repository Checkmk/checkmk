<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import type { HostEntry, HostRef, ServiceState } from '@/monitoring/shared/api/types'
import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import type { CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'
import LabelCell from '@/monitoring/shared/components/cell/LabelCell.vue'
import NumberCell from '@/monitoring/shared/components/cell/NumberCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import { hostServicesPageUrl } from '@/monitoring/shared/hostServicesPageUrl'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'

const props = withDefaults(
  defineProps<{
    row: HostEntry
    tableRow: Row<HostEntry>
    // Always-visible inline buttons; their url may contain a {host} placeholder resolved per row.
    rowActions?: CellAction[]
    // Lazy loader for the overflow menu entries of this host.
    loadActionMenu?: ((host: HostRef) => Promise<CellAction[]>) | undefined
  }>(),
  { rowActions: () => [], loadActionMenu: undefined }
)

const emit = defineEmits<{
  (event: 'open', host: HostEntry): void
  (event: 'command', payload: { id: string; target: HostRef }): void
}>()

const { _t } = usei18n()

const SERVICE_COUNT_MIN_WIDTH = 35

const hostRef = computed<HostRef>(() => ({ site_id: props.row.site_id, name: props.row.name }))

const actionButtons = computed<CellAction[]>(() =>
  props.rowActions.map((action) => ({
    ...action,
    url: action.url?.replace('{host}', encodeURIComponent(props.row.name))
  }))
)

function onActionSelect(action: CellAction): void {
  emit('command', { id: action.id, target: hostRef.value })
}

const allServicesLink = computed<CellLink>(() => ({
  href: hostServicesPageUrl(hostRef.value),
  target: '_top'
}))

function servicesInStateLink(state: ServiceState): CellLink {
  return { href: hostServicesPageUrl(hostRef.value, [state]), target: '_top' }
}

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

function toggleSelected(selected: boolean): void {
  props.tableRow.toggleSelected(selected)
}

const labels = computed(() => toLabelItems(props.row.labels ?? {}))
const tags = computed(() => toTagItems(props.row.tags ?? {}))
const contacts = computed(() => toNameItems(props.row.contacts ?? []))
const contactGroups = computed(() => toNameItems(props.row.contact_groups ?? []))

const lastCheck = computed(() =>
  props.row.last_check === undefined ? undefined : formatTimestamp(props.row.last_check)
)
const lastStateChange = computed(() =>
  props.row.last_state_change === undefined
    ? undefined
    : formatTimestamp(props.row.last_state_change)
)
</script>

<template>
  <CheckboxCell
    v-if="hasColumn('select')"
    column-id="select"
    :aria-label="_t('Select host %{name}', { name: row.name })"
    :model-value="tableRow.getIsSelected()"
    @update:model-value="toggleSelected"
  />
  <StateCell v-if="hasColumn('state')" column-id="state" :state="row.state" />
  <IconCell v-if="hasColumn('modes')" column-id="modes" :icons="row.modes ?? []" />
  <StringCell
    v-if="hasColumn('name')"
    column-id="name"
    :value="row.name"
    :button="true"
    @click="emit('open', row)"
  />
  <StringCell v-if="hasColumn('alias')" column-id="alias" :value="row.alias" />
  <StringCell v-if="hasColumn('address')" column-id="address" :value="row.address" />
  <StringCell v-if="hasColumn('folder')" column-id="folder" :value="row.folder" />
  <StringCell v-if="hasColumn('site_id')" column-id="site_id" :value="row.site_id" />
  <NumberCell
    v-if="hasColumn('num_services')"
    column-id="num_services"
    :value="row.num_services"
    :highlight="{
      color: 'default',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services
    }"
    :linked-to="!row.num_services ? undefined : allServicesLink"
  />
  <NumberCell
    v-if="hasColumn('num_services_ok')"
    column-id="num_services_ok"
    :value="row.num_services_ok"
    :highlight="{
      color: 'success',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services_ok
    }"
    :linked-to="!row.num_services_ok ? undefined : servicesInStateLink('OK')"
  />
  <NumberCell
    v-if="hasColumn('num_services_warn')"
    column-id="num_services_warn"
    :value="row.num_services_warn"
    :highlight="{
      color: 'warning',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services_warn
    }"
    :linked-to="!row.num_services_warn ? undefined : servicesInStateLink('WARN')"
  />
  <NumberCell
    v-if="hasColumn('num_services_crit')"
    column-id="num_services_crit"
    :value="row.num_services_crit"
    :highlight="{
      color: 'danger',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services_crit
    }"
    :linked-to="!row.num_services_crit ? undefined : servicesInStateLink('CRIT')"
  />
  <NumberCell
    v-if="hasColumn('num_services_unknown')"
    column-id="num_services_unknown"
    :value="row.num_services_unknown"
    :highlight="{
      color: 'unknown',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services_unknown
    }"
    :linked-to="!row.num_services_unknown ? undefined : servicesInStateLink('UNKNOWN')"
  />
  <NumberCell
    v-if="hasColumn('num_services_pending')"
    column-id="num_services_pending"
    :value="row.num_services_pending"
    :highlight="{
      color: 'pending',
      minWidth: SERVICE_COUNT_MIN_WIDTH,
      active: !!row.num_services_pending
    }"
    :linked-to="
      !row.num_services_pending
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_pending`,
            target: '_top'
          }
    "
  />

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
  <StringCell v-if="hasColumn('customer')" column-id="customer" :value="row.customer" />

  <ActionsCell
    v-if="(loadActionMenu || actionButtons.length > 0) && hasColumn('actions')"
    column-id="actions"
    :actions="actionButtons"
    :max-visible="actionButtons.length"
    :load="loadActionMenu ? () => loadActionMenu!(hostRef) : undefined"
    @select="onActionSelect"
  />
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-base-cell {
  color: var(--font-color-secondary);
}
</style>
