<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed } from 'vue'

import CmkDeltaArrow from '../CmkDeltaArrow.vue'
import type {
  CmkRankedTableProps,
  RankedTableCell,
  RankedTableColumn,
  RankedTableRow
} from './types'

const {
  columns,
  rows,
  barColor = 'var(--color-light-blue-50)'
} = defineProps<CmkRankedTableProps>()

const emit = defineEmits<{
  /** A cell in a column marked `clickable` was activated. */
  cellClick: [column: RankedTableColumn, row: RankedTableRow]
}>()

// Canonical SI byte formatter (base 1000), matching the backend: 90_400_000_000 → "90.40 GB".
const byteFormatter = new SIFormatter('B', { type: 'strict', digits: 2 })

// Largest value per bar column, used to scale bars of columns without a fixed `barRange`.
const columnMax = computed<Record<string, number>>(() => {
  const max: Record<string, number> = {}
  for (const column of columns) {
    if (column.bar && column.barRange === undefined) {
      max[column.key] = Math.max(0, ...rows.map((row) => Number(cell(column, row).value ?? 0)))
    }
  }
  return max
})

function cell(column: RankedTableColumn, row: RankedTableRow): RankedTableCell {
  const value = row[column.key]
  return typeof value === 'object' ? value : { value: value ?? '' }
}

function isNumeric(column: RankedTableColumn): boolean {
  return column.render === 'bytes' || column.render === 'count' || column.render === 'delta'
}

/** Which way a delta cell's arrow points, or null for a change without one. */
function deltaDirection(column: RankedTableColumn, row: RankedTableRow): 'up' | 'down' | null {
  const value = Number(cell(column, row).value ?? 0)
  if (!Number.isFinite(value) || value === 0) {
    return null
  }
  return value > 0 ? 'up' : 'down'
}

function cellText(column: RankedTableColumn, row: RankedTableRow): string {
  const { value, formatted } = cell(column, row)
  if (formatted !== undefined) {
    return formatted
  }
  if (column.render === 'bytes') {
    return byteFormatter.render(Number(value ?? 0))
  }
  return String(value ?? '')
}

function barPercent(column: RankedTableColumn, row: RankedTableRow): number {
  const value = Number(cell(column, row).value ?? 0)
  if (column.barRange !== undefined) {
    const [minimum, maximum] = column.barRange
    if (maximum <= minimum) {
      // A collapsed range carries no proportion: everything that reaches it is full.
      return value >= maximum ? 100 : 0
    }
    return Math.min(100, Math.max(0, ((value - minimum) / (maximum - minimum)) * 100))
  }
  const max = columnMax.value[column.key] ?? 0
  return max > 0 ? (value / max) * 100 : 0
}

function barColorOf(column: RankedTableColumn, row: RankedTableRow): string {
  return cell(column, row).color ?? barColor
}
</script>

<template>
  <table class="db-cmk-ranked-table">
    <thead>
      <tr>
        <th
          v-for="column in columns"
          :key="column.key"
          class="db-cmk-ranked-table__th"
          :class="{
            'db-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar,
            'db-cmk-ranked-table__cell--fit': !column.bar
          }"
        >
          {{ column.title }}
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, index) in rows" :key="index" class="db-cmk-ranked-table__row">
        <td
          v-for="column in columns"
          :key="column.key"
          class="db-cmk-ranked-table__td"
          :class="{
            'db-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar,
            'db-cmk-ranked-table__cell--fit': !column.bar
          }"
        >
          <div v-if="column.bar" class="db-cmk-ranked-table__bar">
            <span class="db-cmk-ranked-table__bar-track">
              <span
                class="db-cmk-ranked-table__bar-fill"
                :style="{
                  width: `${barPercent(column, row)}%`,
                  backgroundColor: barColorOf(column, row)
                }"
              />
            </span>
            <span class="db-cmk-ranked-table__bar-value">{{ cellText(column, row) }}</span>
          </div>
          <CmkButton
            v-else-if="cell(column, row).href !== undefined"
            variant="text"
            size="small"
            :href="cell(column, row).href"
          >
            {{ cellText(column, row) }}
          </CmkButton>
          <CmkButton
            v-else-if="column.clickable"
            variant="text"
            size="small"
            @click="emit('cellClick', column, row)"
          >
            {{ cellText(column, row) }}
          </CmkButton>
          <span v-else-if="column.render === 'delta'" class="db-cmk-ranked-table__delta">
            <CmkDeltaArrow
              v-if="deltaDirection(column, row) !== null"
              :direction="deltaDirection(column, row)!"
            />
            {{ cellText(column, row) }}
          </span>
          <template v-else>{{ cellText(column, row) }}</template>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.db-cmk-ranked-table {
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

.db-cmk-ranked-table__th {
  padding: clamp(2px, 2cqh, 8px) clamp(6px, 1cqw, 12px);
  font-size: 0.85em;
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
  text-align: left;
  letter-spacing: 0.04em;
  white-space: nowrap;
  border-bottom: 1px solid var(--ux-theme-4);
}

.db-cmk-ranked-table__td {
  padding: clamp(2px, 2cqh, 8px) clamp(6px, 1cqw, 12px);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* Zebra striping, using the shared alternating-row background tokens. */
.db-cmk-ranked-table__row:nth-child(odd) {
  background-color: var(--odd-tr-bg-color);
}

.db-cmk-ranked-table__row:nth-child(even) {
  background-color: var(--even-tr-bg-color);
}

.db-cmk-ranked-table__cell--right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.db-cmk-ranked-table__cell--fit {
  width: 1%;
}

.db-cmk-ranked-table__bar {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1cqw, 12px);
}

.db-cmk-ranked-table__bar-track {
  flex: 1;

  /* Keeps the bar visible when the text columns claim most of the width -- without
     it the track is the only flexible box in the row and collapses to nothing. */
  min-width: 4em;
  height: clamp(4px, 1.2cqh, 7px);
  overflow: hidden;
  background-color: var(--ux-theme-4);
  border-radius: 99999px;
}

.db-cmk-ranked-table__bar-fill {
  display: block;
  height: 100%;
  border-radius: 99999px;
}

/* Right-aligned like the other numeric columns, with the arrow riding along
   the end of the figure rather than sitting in a column of its own. */
.db-cmk-ranked-table__delta {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  justify-content: flex-end;
}

.db-cmk-ranked-table__bar-value {
  min-width: 5.5em;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
