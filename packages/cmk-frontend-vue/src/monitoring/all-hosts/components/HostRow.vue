<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { HostEntry } from '@/monitoring/shared/api/types'
import NumberCell from '@/monitoring/shared/components/cell/NumberCell.vue'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import type { CellHighlight } from '@/monitoring/shared/components/cell/base/highlight'

defineProps<{
  row: HostEntry
}>()

const OK_HIGHLIGHT: CellHighlight = { type: 'inline', color: 'success' }
const WARN_HIGHLIGHT: CellHighlight = { type: 'inline', color: 'warning' }
const CRIT_HIGHLIGHT: CellHighlight = { type: 'inline', color: 'danger' }
const UNKNOWN_HIGHLIGHT: CellHighlight = { type: 'inline', color: 'default' }
const PENDING_HIGHLIGHT: CellHighlight = { type: 'outline', color: 'default' }
</script>

<template>
  <StateCell column-id="state" :state="row.state" />
  <StringCell
    column-id="name"
    :value="row.name"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host`,
      target: '_top',
      variant: 'icon'
    }"
  />
  <StringCell column-id="alias" :value="row.alias" />
  <StringCell column-id="address" :value="row.address" />
  <NumberCell
    column-id="num_services_ok"
    :value="row.num_services_ok"
    :highlight="OK_HIGHLIGHT"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host_ok`,
      target: '_top'
    }"
  />
  <NumberCell
    column-id="num_services_warn"
    :value="row.num_services_warn"
    :highlight="WARN_HIGHLIGHT"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host_warn`,
      target: '_top'
    }"
  />
  <NumberCell
    column-id="num_services_crit"
    :value="row.num_services_crit"
    :highlight="CRIT_HIGHLIGHT"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host_crit`,
      target: '_top'
    }"
  />
  <NumberCell
    column-id="num_services_unknown"
    :value="row.num_services_unknown"
    :highlight="UNKNOWN_HIGHLIGHT"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host_unknown`,
      target: '_top'
    }"
  />
  <NumberCell
    column-id="num_services_pending"
    :value="row.num_services_pending"
    :highlight="PENDING_HIGHLIGHT"
    :linked-to="{
      href: `view.py?host=${row.name}&view_name=host_pending`,
      target: '_top'
    }"
  />
</template>
