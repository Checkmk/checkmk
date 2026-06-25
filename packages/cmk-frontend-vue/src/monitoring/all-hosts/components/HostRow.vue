<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Row } from '@tanstack/vue-table'
import { inject } from 'vue'

import type { HostEntry } from '@/monitoring/shared/api/types'
import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import NumberCell from '@/monitoring/shared/components/cell/NumberCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'

const props = defineProps<{
  row: HostEntry
  tableRow: Row<HostEntry>
}>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

function hasColumn(columnId: string): boolean {
  return columns?.value.has(columnId) ?? true
}

function toggleSelected(selected: boolean): void {
  props.tableRow.toggleSelected(selected)
}
</script>

<template>
  <CheckboxCell
    v-if="hasColumn('select')"
    column-id="select"
    :model-value="tableRow.getIsSelected()"
    @update:model-value="toggleSelected"
  />
  <StateCell v-if="hasColumn('state')" column-id="state" :state="row.state" />
  <StringCell v-if="hasColumn('name')" column-id="name" :value="row.name" />
  <StringCell v-if="hasColumn('alias')" column-id="alias" :value="row.alias" />
  <StringCell v-if="hasColumn('address')" column-id="address" :value="row.address" />
  <NumberCell
    v-if="hasColumn('num_services')"
    column-id="num_services"
    :value="row.num_services"
    :tag-properties="{
      variant: 'fill',
      color: 'default'
    }"
    :linked-to="
      row.num_services === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host`,
            target: '_top'
          }
    "
  />
  <NumberCell
    v-if="hasColumn('num_services_ok')"
    column-id="num_services_ok"
    :value="row.num_services_ok"
    :tag-properties="
      row.num_services_ok === 0
        ? undefined
        : {
            variant: 'weighted',
            color: 'success'
          }
    "
    :linked-to="
      row.num_services_ok === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_ok`,
            target: '_top'
          }
    "
  />
  <NumberCell
    v-if="hasColumn('num_services_warn')"
    column-id="num_services_warn"
    :value="row.num_services_warn"
    :tag-properties="
      row.num_services_warn === 0
        ? undefined
        : {
            variant: 'weighted',
            color: 'warning'
          }
    "
    :linked-to="
      row.num_services_warn === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_warn`,
            target: '_top'
          }
    "
  />
  <NumberCell
    v-if="hasColumn('num_services_crit')"
    column-id="num_services_crit"
    :value="row.num_services_crit"
    :tag-properties="
      row.num_services_crit === 0
        ? undefined
        : {
            variant: 'weighted',
            color: 'danger'
          }
    "
    :linked-to="
      row.num_services_crit === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_crit`,
            target: '_top'
          }
    "
  />
  <NumberCell
    v-if="hasColumn('num_services_unknown')"
    column-id="num_services_unknown"
    :value="row.num_services_unknown"
    :tag-properties="
      row.num_services_unknown === 0
        ? undefined
        : {
            variant: 'weighted',
            color: 'unknown'
          }
    "
    :linked-to="
      row.num_services_unknown === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_unknown`,
            target: '_top'
          }
    "
  />
  <NumberCell
    v-if="hasColumn('num_services_pending')"
    column-id="num_services_pending"
    :value="row.num_services_pending"
    :tag-properties="
      row.num_services_pending === 0
        ? undefined
        : {
            variant: 'weighted',
            color: 'default'
          }
    "
    :linked-to="
      row.num_services_pending === 0
        ? undefined
        : {
            href: `view.py?host=${row.name}&view_name=host_pending`,
            target: '_top'
          }
    "
  />
</template>
