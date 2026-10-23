<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { computed } from 'vue'

import ContextualLinkChooser from '../ContextualLinkChooser.vue'
import type {
  CmkRankedTableProps,
  RankedTableCell,
  RankedTableColumn,
  RankedTableRow
} from './types'

const { columns, rows } = defineProps<CmkRankedTableProps>()

const DEFAULT_BAR_COLOR = 'var(--status-color-info)'

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
  return column.render === 'count'
}

function cellText(column: RankedTableColumn, row: RankedTableRow): string {
  const { value, formatted } = cell(column, row)
  if (formatted !== undefined) {
    return formatted
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
  return cell(column, row).color ?? DEFAULT_BAR_COLOR
}

/** Whether a column's text may be cut with an ellipsis when the width runs short. */
function truncates(column: RankedTableColumn): boolean {
  return !column.bar && !isNumeric(column)
}

/** Links carry their own tooltip, so only plain text cells get one on the cell. */
function plainTextTooltip(column: RankedTableColumn, row: RankedTableRow): string | undefined {
  const { href, choices } = cell(column, row)
  const isPlain = href === undefined && choices === undefined
  return truncates(column) && isPlain ? cellText(column, row) : undefined
}

// Text columns hug their content but give way first; figures never shrink, and the
// bar column takes the remaining space.
const gridTemplateColumns = computed(() =>
  columns
    .map((column) => {
      if (column.bar) {
        return 'minmax(max-content, 1fr)'
      }
      return truncates(column) ? 'minmax(2.5em, max-content)' : 'max-content'
    })
    .join(' ')
)
</script>

<template>
  <div class="db-cmk-ranked-table">
    <table class="db-cmk-ranked-table__table" role="table" :style="{ gridTemplateColumns }">
      <thead role="rowgroup">
        <tr class="db-cmk-ranked-table__row db-cmk-ranked-table__row--head" role="row">
          <th
            v-for="column in columns"
            :key="column.key"
            class="db-cmk-ranked-table__th"
            :class="{ 'db-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar }"
            :title="truncates(column) ? column.title : undefined"
            role="columnheader"
          >
            {{ column.title }}
          </th>
        </tr>
      </thead>
      <tbody role="rowgroup">
        <tr
          v-for="(row, index) in rows"
          :key="index"
          class="db-cmk-ranked-table__row db-cmk-ranked-table__row--body"
          role="row"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            class="db-cmk-ranked-table__td"
            :class="{ 'db-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar }"
            :title="plainTextTooltip(column, row)"
            role="cell"
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
            <ContextualLinkChooser
              v-else-if="cell(column, row).choices !== undefined"
              :entries="cell(column, row).choices!"
            >
              <CmkButton
                class="db-cmk-ranked-table__link"
                variant="text"
                size="small"
                :title="cellText(column, row)"
              >
                <span class="db-cmk-ranked-table__text">{{ cellText(column, row) }}</span>
              </CmkButton>
            </ContextualLinkChooser>
            <CmkButton
              v-else-if="cell(column, row).href !== undefined"
              class="db-cmk-ranked-table__link"
              variant="text"
              size="small"
              :href="cell(column, row).href"
              :title="cellText(column, row)"
            >
              <span class="db-cmk-ranked-table__text">{{ cellText(column, row) }}</span>
            </CmkButton>
            <span v-else class="db-cmk-ranked-table__text">{{ cellText(column, row) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
/* The wrapper scrolls; the table never clips its own rows. */
.db-cmk-ranked-table {
  width: 100%;
  height: 100%;
  overflow: auto;

  /* Set here rather than on the table, so the container query below and the bar's
     minimum widths are measured in the same em. */
  font-size: var(--font-size-normal);
  container-type: inline-size;
}

/* A grid instead of the table layout algorithm: its tracks can hug their content
   and still shrink below it, which table cells cannot. */
.db-cmk-ranked-table__table {
  display: grid;
  width: 100%;
}

.db-cmk-ranked-table__table thead,
.db-cmk-ranked-table__table tbody {
  display: contents;
}

.db-cmk-ranked-table__row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
}

/* Stays in view while the rows scroll beneath it. */
.db-cmk-ranked-table__row--head {
  position: sticky;
  top: 0;
  z-index: 1;
  background-color: var(--even-tr-bg-color);
}

.db-cmk-ranked-table__th {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: var(--dimension-3) var(--dimension-4);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  color: var(--font-color-muted);
  text-align: left;
  letter-spacing: 0.04em;
  white-space: nowrap;
  border-bottom: 1px solid var(--ux-theme-4);
}

.db-cmk-ranked-table__td {
  min-width: 0;
  padding: var(--dimension-3) var(--dimension-4);
  white-space: nowrap;
}

/* Zebra striping, using the shared alternating-row background tokens. */
.db-cmk-ranked-table__row--body:nth-child(odd) {
  background-color: var(--odd-tr-bg-color);
}

.db-cmk-ranked-table__row--body:nth-child(even) {
  background-color: var(--even-tr-bg-color);
}

.db-cmk-ranked-table__cell--right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.db-cmk-ranked-table__text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

.db-cmk-ranked-table__link {
  max-width: 100%;
}

.db-cmk-ranked-table__bar {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

/* Text columns give way before the bar does; only a table too narrow for a
   meaningful bar drops it, so that the figures beside it keep their room. */
.db-cmk-ranked-table__bar-track {
  flex: 1;
  min-width: 4em;
  height: var(--dimension-3);
  overflow: hidden;
  background-color: var(--ux-theme-4);
  border-radius: 99999px;
}

@container (width < 24em) {
  .db-cmk-ranked-table__bar-track {
    display: none;
  }
}

.db-cmk-ranked-table__bar-fill {
  display: block;
  height: 100%;
  border-radius: 99999px;
}

.db-cmk-ranked-table__bar-value {
  flex-shrink: 0;
  min-width: 5.5em;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
