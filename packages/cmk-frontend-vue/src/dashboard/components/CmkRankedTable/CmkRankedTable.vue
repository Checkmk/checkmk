<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeUpdate, onUpdated, useTemplateRef } from 'vue'

import type { ContextualLinkEntry } from '@/dashboard/lib/contextualLinkUrl'

import ContextualLinkAnchor from '../ContextualLinkAnchor.vue'
import ContextualLinkArrow from '../ContextualLinkArrow.vue'
import RankedTableStandIn from './RankedTableStandIn.vue'
import type {
  CmkRankedTableProps,
  RankedTableCell,
  RankedTableColumn,
  RankedTableRow
} from './types'
import { type BarTarget, useRankedTableTween } from './useRankedTableTween'

const {
  columns,
  rows,
  placeholder,
  busy = false,
  showRank = false,
  label,
  rowKey = (_row, index) => String(index)
} = defineProps<CmkRankedTableProps>()

const { _t } = usei18n()

defineSlots<{
  /** Shown above the faded stand-ins of an `empty` placeholder. */
  empty?(): unknown
}>()

// Largest distance from zero per bar column, used to scale bars of columns without a fixed
// `barRange`: their bars grow from zero, so a negative value is as long as its size.
const columnMax = computed<Record<string, number>>(() => {
  const max: Record<string, number> = {}
  for (const column of columns) {
    if (column.bar && column.barRange === undefined) {
      max[column.key] = Math.max(
        0,
        ...rows.map((row) => Math.abs(Number(cell(column, row).value ?? 0)))
      )
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

function proportion(column: RankedTableColumn, value: number): number {
  if (column.barRange !== undefined) {
    const [minimum, maximum] = column.barRange
    if (maximum <= minimum) {
      // A collapsed range carries no proportion: everything that reaches it is full.
      return value >= maximum ? 100 : 0
    }
    return Math.min(100, Math.max(0, ((value - minimum) / (maximum - minimum)) * 100))
  }
  const max = columnMax.value[column.key] ?? 0
  return max > 0 ? (Math.abs(value) / max) * 100 : 0
}

// Any bar above the bottom of its range stays visible as a sliver.
const MINIMUM_BAR_PERCENT = 2

function barPercent(column: RankedTableColumn, row: RankedTableRow): number {
  const percent = proportion(column, Number(cell(column, row).value ?? 0))
  return percent <= 0 ? 0 : Math.max(MINIMUM_BAR_PERCENT, percent)
}

/** Whether a column's text may be cut with an ellipsis when the width runs short. */
function truncates(column: RankedTableColumn): boolean {
  return !column.bar && !isNumeric(column)
}

/** Where a cell leads: one link, several to choose from, or none. */
function linkEntries(column: RankedTableColumn, row: RankedTableRow): ContextualLinkEntry[] {
  const { href, choices } = cell(column, row)
  if (choices !== undefined) {
    return choices
  }
  return href === undefined ? [] : [{ title: cellText(column, row), href }]
}

/** Links carry their own tooltip, so only plain text cells get one on the cell. */
function plainTextTooltip(column: RankedTableColumn, row: RankedTableRow): string | undefined {
  const { href, choices } = cell(column, row)
  const isPlain = href === undefined && choices === undefined
  return truncates(column) && isPlain ? cellText(column, row) : undefined
}

function cellClasses(column: RankedTableColumn): Record<string, boolean> {
  return {
    'db-cmk-ranked-table__cell--right': isNumeric(column) || column.bar,
    'db-cmk-ranked-table__cell--secondary': column.tone === 'secondary'
  }
}

const isBusy = computed(() => busy || placeholder?.kind === 'loading')

// A row count from configuration may be anything; `v-for` throws on a negative one.
const standInRowCount = computed(() => Math.max(0, Math.floor(placeholder?.rows ?? 0)))

function barKey(rowKeyValue: string, column: RankedTableColumn): string {
  return `${rowKeyValue}\u0000${column.key}`
}

const bars = useRankedTableTween(() => {
  const targets = new Map<string, BarTarget>()
  rows.forEach((row, index) => {
    for (const column of columns) {
      if (column.bar) {
        targets.set(barKey(rowKey(row, index), column), {
          percent: barPercent(column, row),
          text: cellText(column, row),
          unit: cell(column, row).unit
        })
      }
    }
  })
  return targets
})

function shownBarPercent(column: RankedTableColumn, row: RankedTableRow, index: number): number {
  return bars.value.get(barKey(rowKey(row, index), column))?.percent ?? barPercent(column, row)
}

/** The value as it counts towards its new one; `undefined` once it has arrived. */
function countingText(
  column: RankedTableColumn,
  row: RankedTableRow,
  index: number
): string | undefined {
  if (!column.bar) {
    return undefined
  }
  const text = bars.value.get(barKey(rowKey(row, index), column))?.text
  return text === undefined || text === cellText(column, row) ? undefined : text
}

const tbody = useTemplateRef<HTMLElement>('tbody')

// Re-ranked rows move in the DOM, which drops the focus they hold: put it back where it was. A
// row that left the table hands its focus to the row now in its place.
let focusedCell: { element: HTMLElement; row: string; position: number; column: string } | undefined
let restoringFocus = false

function bodyRows(): HTMLElement[] {
  return [...(tbody.value?.querySelectorAll<HTMLElement>('[data-row-key]') ?? [])]
}

onBeforeUpdate(() => {
  focusedCell = undefined
  const element = document.activeElement
  if (!(element instanceof HTMLElement) || !tbody.value?.contains(element)) {
    return
  }
  const tr = element.closest<HTMLElement>('[data-row-key]')
  const column = element.closest<HTMLElement>('[data-column-key]')?.dataset.columnKey
  if (tr?.dataset.rowKey !== undefined && column !== undefined) {
    focusedCell = { element, row: tr.dataset.rowKey, position: bodyRows().indexOf(tr), column }
  }
})

onUpdated(() => {
  if (focusedCell === undefined || document.activeElement === focusedCell.element) {
    return
  }
  const { row, position, column } = focusedCell
  const trs = bodyRows()
  const tr =
    trs.find((candidate) => candidate.dataset.rowKey === row) ??
    trs[Math.min(position, trs.length - 1)]
  const target = tr?.querySelector<HTMLElement>(`[data-column-key="${CSS.escape(column)}"] a`)
  // Focus that only follows its row must not scroll a page the reader has moved on from.
  restoringFocus = true
  target?.focus({ preventScroll: true })
  restoringFocus = false
})

// The sticky header would cover a row focused at the top edge.
function revealFocusedRow(event: FocusEvent): void {
  if (restoringFocus || !(event.target instanceof Element)) {
    return
  }
  const row = event.target.closest<HTMLElement>('[data-row-key]')
  const header = row?.closest('table')?.querySelector<HTMLElement>('thead tr')
  if (row && header) {
    row.style.scrollMarginTop = `${header.offsetHeight}px`
    row.scrollIntoView({ block: 'nearest' })
  }
}

// Varied widths make the stand-in rows read as text rather than as a grid of boxes.
const STAND_IN_TEXT_WIDTHS = ['9em', '6.5em', '11em', '7.5em', '10em']

function standInWidth(column: RankedTableColumn, rowIndex: number, columnIndex: number): string {
  if (isNumeric(column) || column.bar) {
    return '3.5em'
  }
  return STAND_IN_TEXT_WIDTHS[(rowIndex + columnIndex * 2) % STAND_IN_TEXT_WIDTHS.length]!
}

// Text columns hug their content but give way first; figures shrink only down to 62px, and a
// bar takes the remaining space in its own track, left of its value. Without a bar, the last
// column takes that space, so that separators and hover span the whole row.
const gridTemplateColumns = computed(() => {
  const tracks = [
    ...(showRank ? ['max-content'] : []),
    ...columns.flatMap((column) => {
      if (column.bar) {
        return ['minmax(min-content, 1fr)', 'minmax(62px, max-content)']
      }
      if (isNumeric(column)) {
        return ['minmax(62px, max-content)']
      }
      return ['minmax(2.5em, max-content)']
    })
  ]
  if (!columns.some((column) => column.bar) && tracks.length > 0) {
    tracks[tracks.length - 1] = tracks.at(-1)!.replace('max-content)', '1fr)')
  }
  return tracks.join(' ')
})
</script>

<template>
  <div
    class="db-cmk-ranked-table"
    :class="{ 'db-cmk-ranked-table--empty': placeholder?.kind === 'empty' }"
  >
    <table
      class="db-cmk-ranked-table__table"
      role="table"
      :aria-label="label"
      :style="{ gridTemplateColumns }"
      :aria-busy="isBusy ? 'true' : undefined"
      :aria-hidden="placeholder?.kind === 'empty' ? 'true' : undefined"
    >
      <thead role="rowgroup">
        <tr class="db-cmk-ranked-table__row db-cmk-ranked-table__row--head" role="row">
          <th
            v-if="showRank"
            class="db-cmk-ranked-table__th db-cmk-ranked-table__rank"
            role="columnheader"
            :aria-label="_t('Rank')"
          >
            <span aria-hidden="true">#</span>
          </th>
          <th
            v-for="column in columns"
            :key="column.key"
            class="db-cmk-ranked-table__th"
            :class="{
              'db-cmk-ranked-table__cell--right': isNumeric(column) && !column.bar,
              'db-cmk-ranked-table__th--bar': column.bar
            }"
            :title="truncates(column) ? column.title : undefined"
            role="columnheader"
          >
            <RankedTableStandIn
              v-if="placeholder && column.title === ''"
              :animated="placeholder.kind === 'loading'"
              width="6em"
            />
            <template v-else>{{ column.title }}</template>
          </th>
        </tr>
      </thead>
      <tbody v-if="placeholder" role="rowgroup">
        <tr
          v-for="rowIndex in standInRowCount"
          :key="rowIndex"
          class="db-cmk-ranked-table__row db-cmk-ranked-table__row--body"
          role="row"
        >
          <td
            v-if="showRank"
            class="db-cmk-ranked-table__td db-cmk-ranked-table__rank"
            role="cell"
          />
          <template v-for="(column, columnIndex) in columns" :key="column.key">
            <td v-if="column.bar" class="db-cmk-ranked-table__td" aria-hidden="true">
              <RankedTableStandIn
                class="db-cmk-ranked-table__bar"
                :animated="placeholder.kind === 'loading'"
                shape="track"
              />
            </td>
            <td class="db-cmk-ranked-table__td" :class="cellClasses(column)" role="cell">
              <RankedTableStandIn
                class="db-cmk-ranked-table__stand-in"
                :animated="placeholder.kind === 'loading'"
                :width="standInWidth(column, rowIndex, columnIndex)"
              />
            </td>
          </template>
        </tr>
      </tbody>
      <tbody v-else ref="tbody" role="rowgroup" @focusin="revealFocusedRow">
        <tr
          v-for="(row, index) in rows"
          :key="rowKey(row, index)"
          class="db-cmk-ranked-table__row db-cmk-ranked-table__row--body"
          role="row"
          :aria-label="showRank ? _t('Rank %{rank}', { rank: `${index + 1}` }) : undefined"
          :data-row-key="rowKey(row, index)"
        >
          <td v-if="showRank" class="db-cmk-ranked-table__td db-cmk-ranked-table__rank" role="cell">
            {{ index + 1 }}
          </td>
          <template v-for="column in columns" :key="column.key">
            <td v-if="column.bar" class="db-cmk-ranked-table__td" aria-hidden="true">
              <span class="db-cmk-ranked-table__bar">
                <span
                  class="db-cmk-ranked-table__bar-fill"
                  :style="{
                    width: `${shownBarPercent(column, row, index)}%`,
                    backgroundColor: cell(column, row).color
                  }"
                />
              </span>
            </td>
            <td
              class="db-cmk-ranked-table__td"
              :class="cellClasses(column)"
              :title="plainTextTooltip(column, row)"
              :data-column-key="column.key"
              role="cell"
            >
              <ContextualLinkAnchor
                v-if="linkEntries(column, row).length > 0"
                v-slot="{ several }"
                :entries="linkEntries(column, row)"
                :title="cellText(column, row)"
              >
                <span class="db-contextual-link-anchor__text db-cmk-ranked-table__text"
                  >{{ cellText(column, row)
                  }}<span v-if="cell(column, row).unit" class="db-cmk-ranked-table__unit">{{
                    ` ${cell(column, row).unit}`
                  }}</span></span
                >
                <ContextualLinkArrow v-if="several" />
              </ContextualLinkAnchor>
              <span v-else class="db-cmk-ranked-table__text"
                ><template v-if="countingText(column, row, index) !== undefined"
                  ><span aria-hidden="true">{{ countingText(column, row, index) }}</span
                  ><span class="db-cmk-ranked-table__visually-hidden">{{
                    cellText(column, row)
                  }}</span></template
                ><template v-else>{{ cellText(column, row) }}</template
                ><span v-if="cell(column, row).unit" class="db-cmk-ranked-table__unit">{{
                  ` ${cell(column, row).unit}`
                }}</span></span
              >
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <div v-if="placeholder?.kind === 'empty'" class="db-cmk-ranked-table__empty-message">
      <slot name="empty" />
    </div>
  </div>
</template>

<style scoped>
/* The wrapper scrolls; the table never clips its own rows. */
.db-cmk-ranked-table {
  --db-cmk-ranked-table-bar-color: var(--color-light-blue-50);

  width: 100%;
  height: 100%;
  overflow: auto;
  font-size: var(--font-size-normal);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-ranked-table {
  --db-cmk-ranked-table-bar-color: var(--color-light-blue-70);
}

/* Positioned so it paints above the faded table, whose opacity stacks it on top. */
.db-cmk-ranked-table__empty-message {
  position: relative;
  grid-area: 1 / 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-3);
  padding: var(--dimension-6);
  text-align: center;
}

/* A grid instead of the table layout algorithm: its tracks can hug their content
   and still shrink below it, which table cells cannot. */
.db-cmk-ranked-table__table {
  display: grid;
  column-gap: 10px;
  width: 100%;
}

/* The faded stand-ins share one grid cell with the message and add no height of their
   own: they fill the box, and the message sizes it where the box is shorter. */
.db-cmk-ranked-table--empty {
  display: grid;

  .db-cmk-ranked-table__table {
    grid-area: 1 / 1;
    height: 0;
    min-height: 100%;
    overflow: hidden;
    opacity: 0.45;
  }
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
  padding: 5px var(--dimension-3);
}

/* Stays in view while the rows scroll beneath it. */
.db-cmk-ranked-table__row--head {
  position: sticky;
  top: 0;
  z-index: 1;
  background-color: var(--db-content-bg-color);
}

.db-cmk-ranked-table__row--body + .db-cmk-ranked-table__row--body {
  border-top: 1px solid var(--border-color-separator);
}

.db-cmk-ranked-table__row--body:is(:hover, :focus-within) {
  background-color: var(--background-row-hover);
}

.db-cmk-ranked-table__th {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-default);
  color: var(--font-color-secondary);
  text-align: left;
  white-space: nowrap;
}

/* The metric name heads the bar and the value beside it. */
.db-cmk-ranked-table__th--bar {
  grid-column: span 2;
}

.db-cmk-ranked-table__td {
  min-width: 0;
  white-space: nowrap;
}

.db-cmk-ranked-table__cell--right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Muted and set against the name that follows it. */
.db-cmk-ranked-table__rank {
  font-size: var(--font-size-small);
  color: var(--font-color-secondary);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.db-cmk-ranked-table__text {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.db-cmk-ranked-table__cell--secondary {
  color: var(--font-color-secondary);

  .db-cmk-ranked-table__text {
    font-weight: var(--font-weight-default);
  }
}

.db-cmk-ranked-table__unit {
  font-size: var(--font-size-small);
  color: var(--font-color-secondary);
}

.db-cmk-ranked-table__bar {
  display: block;
  height: var(--dimension-3);
}

.db-cmk-ranked-table__visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* Only the keyboard's focus is marked; a click is its own feedback. The menu of several links
   renders its anchor inside a child component, hence `:deep`. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.db-cmk-ranked-table__row--body :deep(a:focus-visible) {
  outline: 2px solid var(--success);
  outline-offset: 2px;
}

.db-cmk-ranked-table__stand-in {
  display: inline-block;
}

.db-cmk-ranked-table__bar-fill {
  display: block;
  height: 100%;
  background-color: var(--db-cmk-ranked-table-bar-color);
  border-radius: 3px;
}
</style>
