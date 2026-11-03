<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkRankedTable, {
  type RankedTableColumn,
  type RankedTableRow
} from '@/dashboard/components/CmkRankedTable'

const columns: RankedTableColumn[] = [
  { key: 'host', title: 'Host', render: 'text', bar: false },
  { key: 'flows', title: 'Flows', render: 'count', bar: true }
]

const rows: RankedTableRow[] = [
  // A cell is either a bare value, or an object with display overrides.
  { host: { value: '10.0.71.219', href: 'view.py?view_name=host' }, flows: 1284 },
  { host: '10.0.234.247', flows: 967 },
  { host: '10.0.171.51', flows: { value: 411, formatted: '411 flows' } }
]
</script>

<template>
  <CmkRankedTable :columns="columns" :rows="rows" />
</template>
