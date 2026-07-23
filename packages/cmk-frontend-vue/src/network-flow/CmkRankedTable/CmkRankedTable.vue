<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed } from 'vue'

import { chartColorCss } from '../colors'
import type { CmkRankedTableProps, RankedTableColumn, RankedTableRow } from './types'

const props = defineProps<CmkRankedTableProps>()

const emit = defineEmits<{
  /** A cell in a column marked `clickable` was activated. */
  cellClick: [column: RankedTableColumn, row: RankedTableRow]
}>()

const barColorCss = computed<string>(() => chartColorCss(props.barColor))

// Canonical SI byte formatter (base 1000), matching the backend: 90_400_000_000 → "90.40 GB".
const byteFormatter = new SIFormatter('B', { type: 'strict', digits: 2 })

// Largest value per bar column, used to scale the inline bars.
const columnMax = computed<Record<string, number>>(() => {
  const max: Record<string, number> = {}
  for (const column of props.columns) {
    if (column.bar) {
      max[column.key] = Math.max(0, ...props.rows.map((row) => Number(row[column.key] ?? 0)))
    }
  }
  return max
})

function isNumeric(column: RankedTableColumn): boolean {
  return column.render === 'bytes' || column.render === 'count'
}

function cellText(column: RankedTableColumn, row: RankedTableRow): string {
  const value = row[column.key]
  if (column.render === 'bytes') {
    return byteFormatter.render(Number(value ?? 0))
  }
  return String(value ?? '')
}

function barPercent(column: RankedTableColumn, row: RankedTableRow): number {
  const max = columnMax.value[column.key] ?? 0
  return max > 0 ? (Number(row[column.key] ?? 0) / max) * 100 : 0
}
</script>

<template>
  <table class="network-flow-cmk-ranked-table">
    <thead>
      <tr>
        <th
          v-for="column in columns"
          :key="column.key"
          class="network-flow-cmk-ranked-table__th"
          :class="{
            'network-flow-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar,
            'network-flow-cmk-ranked-table__cell--fit': !column.bar
          }"
        >
          {{ column.title }}
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, index) in rows" :key="index" class="network-flow-cmk-ranked-table__row">
        <td
          v-for="column in columns"
          :key="column.key"
          class="network-flow-cmk-ranked-table__td"
          :class="{
            'network-flow-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar,
            'network-flow-cmk-ranked-table__cell--fit': !column.bar
          }"
        >
          <div v-if="column.bar" class="network-flow-cmk-ranked-table__bar">
            <span class="network-flow-cmk-ranked-table__bar-track">
              <span
                class="network-flow-cmk-ranked-table__bar-fill"
                :style="{
                  width: `${barPercent(column, row)}%`,
                  backgroundColor: barColorCss
                }"
              />
            </span>
            <span class="network-flow-cmk-ranked-table__bar-value">{{
              cellText(column, row)
            }}</span>
          </div>
          <button
            v-else-if="column.clickable"
            type="button"
            class="network-flow-cmk-ranked-table__link"
            @click="emit('cellClick', column, row)"
          >
            {{ cellText(column, row) }}
          </button>
          <template v-else>{{ cellText(column, row) }}</template>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.network-flow-cmk-ranked-table {
  width: 100%;
  height: 100%;
  border-collapse: collapse;
  overflow: hidden;
  font-size: clamp(11px, 9cqh, 14px);
  container-type: size;

  /* Text columns hug their content (width: 1% + nowrap shrinks them to the
     widest cell); the bar column takes all remaining space, per the design. */
  table-layout: auto;
}

.network-flow-cmk-ranked-table__th {
  padding: clamp(2px, 2cqh, 8px) clamp(6px, 1cqw, 12px);
  font-size: 0.85em;
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
  border-bottom: 1px solid var(--ux-theme-4);
}

.network-flow-cmk-ranked-table__td {
  padding: clamp(2px, 2cqh, 8px) clamp(6px, 1cqw, 12px);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* Zebra striping, using the shared alternating-row background tokens. */
.network-flow-cmk-ranked-table__row:nth-child(odd) {
  background-color: var(--odd-tr-bg-color);
}

.network-flow-cmk-ranked-table__row:nth-child(even) {
  background-color: var(--even-tr-bg-color);
}

.network-flow-cmk-ranked-table__cell--right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.network-flow-cmk-ranked-table__cell--fit {
  width: 1%;
}

.network-flow-cmk-ranked-table__bar {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1cqw, 12px);
}

.network-flow-cmk-ranked-table__bar-track {
  flex: 1;
  height: clamp(4px, 1.2cqh, 7px);
  overflow: hidden;
  background-color: var(--ux-theme-4);
  border-radius: 99999px;
}

.network-flow-cmk-ranked-table__bar-fill {
  display: block;
  height: 100%;
  border-radius: 99999px;
}

.network-flow-cmk-ranked-table__bar-value {
  min-width: 5.5em;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

/* Clickable cell: a bare button styled like CmkLink. */
.network-flow-cmk-ranked-table__link {
  padding: 0;
  font: inherit;
  color: inherit;
  text-decoration: underline;
  cursor: pointer;
  background: none;
  border: none;
}

.network-flow-cmk-ranked-table__link:hover {
  color: var(--cmk-link-hover-color, #15d1a0);
}
</style>
