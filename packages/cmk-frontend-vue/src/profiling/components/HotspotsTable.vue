<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useVirtualizer } from '@tanstack/vue-virtual'
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type ComponentPublicInstance, computed, ref, watch } from 'vue'

import type { HotspotData } from '../types'
import { heatColor } from '../utils/flamegraph-colors'
import { formatCalls, formatMs, formatPercent } from '../utils/format'

type SortKey = 'self_time_ms' | 'cumulative_time_ms' | 'ncalls' | 'function' | 'ms_per_call'

interface EnrichedHotspot extends HotspotData {
  ms_per_call: number
}

const props = defineProps<{
  hotspots: HotspotData[]
  highlightFunction: string
  searchQuery: string
}>()

const { _t } = usei18n()

const emit = defineEmits<{
  (e: 'select-function', name: string): void
}>()

const expandedRows = ref<Set<string>>(new Set())

function selectFromTable(name: string) {
  emit('select-function', name)
}

const enrichedHotspots = computed<EnrichedHotspot[]>(() =>
  props.hotspots.map((h) => ({
    ...h,
    // Per-call cost over primitive (non-recursive) calls, matching cProfile's
    // cumulative "percall" column (ct/cc) — recursive re-entries don't inflate it.
    ms_per_call: h.primitive_calls > 0 ? h.cumulative_time_ms / h.primitive_calls : 0
  }))
)

const filteredHotspots = computed(() => {
  const q = props.searchQuery.toLowerCase()
  if (q.length < 2) {
    return enrichedHotspots.value
  }
  return enrichedHotspots.value.filter(
    (h) => h.function.toLowerCase().includes(q) || h.file.toLowerCase().includes(q)
  )
})

const sortKey = ref<SortKey>('self_time_ms')
const sortDir = ref<'asc' | 'desc'>('desc')

const sortedHotspots = computed(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...filteredHotspots.value].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (typeof av === 'string' && typeof bv === 'string') {
      return dir * av.localeCompare(bv)
    }
    return dir * ((av as number) - (bv as number))
  })
})

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortKey.value = key
    sortDir.value = key === 'function' ? 'asc' : 'desc'
  }
  expandedRows.value.clear()
}

function sortIndicator(key: SortKey): string {
  if (sortKey.value !== key) {
    return ''
  }
  return sortDir.value === 'desc' ? ' \u25be' : ' \u25b4'
}

function ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
  if (sortKey.value !== key) {
    return 'none'
  }
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

function toggleRow(fn: string) {
  if (expandedRows.value.has(fn)) {
    expandedRows.value.delete(fn)
  } else {
    expandedRows.value.add(fn)
  }
}

function barWidth(pct: number): number {
  return Math.min(100, Math.max(1, pct))
}

// Row virtualization via @tanstack/vue-virtual (the same primitive the
// monitoring "all hosts" table uses). Only the visible window of function rows
// is kept in the DOM, so a profile with thousands of functions stays cheap.
// Rows have variable height (the expandable caller/callee panel), so each
// <tbody> is measured individually via measureElement.
const scrollContainerRef = ref<HTMLElement | null>(null)
const headerHeight = ref(0)

function measureHeader(): void {
  const thead = scrollContainerRef.value?.querySelector('thead')
  headerHeight.value = thead ? thead.getBoundingClientRect().height : 0
}

const { observe } = useResizeObserver(() => measureHeader())
observe(scrollContainerRef)
watch(
  scrollContainerRef,
  (el) => {
    if (el) {
      measureHeader()
    }
  },
  { immediate: true }
)

const rowVirtualizer = useVirtualizer(
  computed(() => ({
    count: sortedHotspots.value.length,
    getScrollElement: () => scrollContainerRef.value,
    estimateSize: () => 48,
    overscan: 10,
    scrollMargin: headerHeight.value,
    // Key by function name so expansion/measurement survives re-sorting.
    getItemKey: (index: number) => sortedHotspots.value[index]?.function ?? index
  }))
)

const virtualRows = computed(() => rowVirtualizer.value.getVirtualItems())
const totalSize = computed(() => rowVirtualizer.value.getTotalSize())

const paddingTop = computed(() => {
  const first = virtualRows.value[0]
  return first ? Math.max(0, first.start - headerHeight.value) : 0
})
const paddingBottom = computed(() => {
  const last = virtualRows.value[virtualRows.value.length - 1]
  return last ? Math.max(0, totalSize.value - last.end + headerHeight.value) : 0
})

function measureRow(el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) {
    rowVirtualizer.value.measureElement(el)
  }
}

function hotspotAt(index: number): EnrichedHotspot {
  return sortedHotspots.value[index]!
}

const virtualHotspots = computed(() =>
  virtualRows.value.map((virtualRow) => ({ virtualRow, hotspot: hotspotAt(virtualRow.index) }))
)
</script>

<template>
  <div ref="scrollContainerRef" class="profiling-hotspots-table">
    <table class="profiling-hotspots-table__table">
      <thead>
        <tr>
          <th class="profiling-hotspots-table__col-rank" scope="col">#</th>
          <th
            class="profiling-hotspots-table__col-function"
            :aria-sort="ariaSort('function')"
            scope="col"
          >
            <button
              type="button"
              class="profiling-hotspots-table__sort-btn"
              @click="toggleSort('function')"
            >
              {{ _t('Function') }}{{ sortIndicator('function') }}
            </button>
          </th>
          <th
            class="profiling-hotspots-table__col-bar"
            :aria-sort="ariaSort('self_time_ms')"
            scope="col"
          >
            <button
              type="button"
              class="profiling-hotspots-table__sort-btn"
              @click="toggleSort('self_time_ms')"
            >
              {{ _t('Self-time') }}{{ sortIndicator('self_time_ms') }}
            </button>
          </th>
          <th
            class="profiling-hotspots-table__col-bar"
            :aria-sort="ariaSort('cumulative_time_ms')"
            scope="col"
          >
            <button
              type="button"
              class="profiling-hotspots-table__sort-btn"
              @click="toggleSort('cumulative_time_ms')"
            >
              {{ _t('Cumulative') }}{{ sortIndicator('cumulative_time_ms') }}
            </button>
          </th>
          <th
            class="profiling-hotspots-table__col-percall"
            :aria-sort="ariaSort('ms_per_call')"
            scope="col"
          >
            <button
              type="button"
              class="profiling-hotspots-table__sort-btn"
              @click="toggleSort('ms_per_call')"
            >
              <!-- eslint-disable-next-line vue/no-bare-strings-in-template -- unit column label -->
              {{ _t('ms/call') }}{{ sortIndicator('ms_per_call') }}
            </button>
          </th>
          <th
            class="profiling-hotspots-table__col-calls"
            :aria-sort="ariaSort('ncalls')"
            scope="col"
          >
            <button
              type="button"
              class="profiling-hotspots-table__sort-btn"
              @click="toggleSort('ncalls')"
            >
              {{ _t('Calls') }}{{ sortIndicator('ncalls') }}
            </button>
          </th>
          <th class="profiling-hotspots-table__col-toggle" scope="col">
            <span class="profiling-hotspots-table__visually-hidden">
              {{ _t('Expand details') }}
            </span>
          </th>
        </tr>
      </thead>
      <tbody v-if="paddingTop > 0" class="profiling-hotspots-table__spacer" aria-hidden="true">
        <tr>
          <td :colspan="7" :style="{ height: `${paddingTop}px` }"></td>
        </tr>
      </tbody>
      <tbody
        v-for="{ virtualRow, hotspot: h } in virtualHotspots"
        :key="h.function"
        :ref="measureRow"
        :data-index="virtualRow.index"
        class="profiling-hotspots-table__body"
      >
        <!-- Main row -->
        <tr
          class="profiling-hotspots-table__row"
          :class="{
            'profiling-hotspots-table__row--highlighted':
              highlightFunction !== '' && h.function === highlightFunction
          }"
          role="button"
          tabindex="0"
          :aria-label="_t('Select function %1').replace('%1', h.function)"
          @click="selectFromTable(h.function)"
          @keydown.enter.prevent="selectFromTable(h.function)"
          @keydown.space.prevent="selectFromTable(h.function)"
        >
          <td class="profiling-hotspots-table__col-rank">
            <div class="profiling-hotspots-table__rank-cell">
              <span
                class="profiling-hotspots-table__heat-bar"
                :style="{ background: heatColor(h.self_pct) }"
              />
              <span class="profiling-hotspots-table__rank-number">{{ virtualRow.index + 1 }}</span>
            </div>
          </td>
          <td class="profiling-hotspots-table__col-function">
            <div class="profiling-hotspots-table__fn-name">{{ h.function }}</div>
            <div class="profiling-hotspots-table__fn-file">{{ h.file }}:{{ h.line }}</div>
          </td>
          <td class="profiling-hotspots-table__col-bar">
            <div class="profiling-hotspots-table__bar-cell">
              <span class="profiling-hotspots-table__bar-value">
                {{ formatMs(h.self_time_ms) }}
              </span>
              <span class="profiling-hotspots-table__bar-track">
                <span
                  class="profiling-hotspots-table__bar-fill"
                  :style="{
                    width: `${barWidth(h.self_pct)}%`,
                    background: heatColor(h.self_pct)
                  }"
                />
              </span>
              <span class="profiling-hotspots-table__bar-pct">
                {{ formatPercent(h.self_pct) }}
              </span>
            </div>
          </td>
          <td class="profiling-hotspots-table__col-bar">
            <div class="profiling-hotspots-table__bar-cell">
              <span class="profiling-hotspots-table__bar-value">
                {{ formatMs(h.cumulative_time_ms) }}
              </span>
              <span class="profiling-hotspots-table__bar-track">
                <span
                  class="profiling-hotspots-table__bar-fill"
                  :style="{
                    width: `${barWidth(h.cumulative_pct)}%`,
                    background: heatColor(h.cumulative_pct)
                  }"
                />
              </span>
              <span class="profiling-hotspots-table__bar-pct">
                {{ formatPercent(h.cumulative_pct) }}
              </span>
            </div>
          </td>
          <td class="profiling-hotspots-table__col-percall">
            {{ formatMs(h.ms_per_call) }}
          </td>
          <td
            class="profiling-hotspots-table__col-calls"
            :title="
              h.ncalls === h.primitive_calls
                ? _t('Number of calls')
                : _t('Total calls / primitive (non-recursive) calls')
            "
          >
            {{ formatCalls(h.ncalls, h.primitive_calls) }}
          </td>
          <td class="profiling-hotspots-table__col-toggle">
            <CmkIconButton
              v-if="h.top_callers.length > 0 || h.top_callees.length > 0"
              name="tree-closed"
              size="small"
              class="profiling-hotspots-table__toggle-btn"
              :class="{
                'profiling-hotspots-table__toggle-btn--open': expandedRows.has(h.function)
              }"
              :title="_t('Show callers / callees')"
              :aria-label="_t('Show callers / callees')"
              :aria-expanded="expandedRows.has(h.function)"
              @click.stop="toggleRow(h.function)"
              @keydown.enter.stop
              @keydown.space.stop
            />
          </td>
        </tr>

        <!-- Detail row (expandable) -->
        <tr v-if="expandedRows.has(h.function)" class="profiling-hotspots-table__detail-row">
          <td></td>
          <td colspan="6">
            <div class="profiling-hotspots-table__detail-panel">
              <template
                v-for="section in [
                  { title: _t('Called by'), items: h.top_callers },
                  { title: _t('Calls'), items: h.top_callees }
                ]"
                :key="section.title"
              >
                <CmkCatalogPanel
                  v-if="section.items.length > 0"
                  :title="section.title"
                  :open="true"
                  class="profiling-hotspots-table__detail-card"
                >
                  <div
                    v-for="(c, ci) in section.items"
                    :key="ci"
                    class="profiling-hotspots-table__edge-item profiling-hotspots-table__edge-item--clickable"
                    role="button"
                    tabindex="0"
                    :aria-label="_t('Select function %1').replace('%1', c.function)"
                    @click.stop="selectFromTable(c.function)"
                    @keydown.enter.prevent.stop="selectFromTable(c.function)"
                    @keydown.space.prevent.stop="selectFromTable(c.function)"
                  >
                    <div class="profiling-hotspots-table__edge-main">
                      <span class="profiling-hotspots-table__edge-fn">{{ c.function }}</span>
                    </div>
                    <div class="profiling-hotspots-table__edge-stats">
                      <span class="profiling-hotspots-table__edge-bar-track">
                        <span
                          class="profiling-hotspots-table__edge-bar-fill"
                          :style="{
                            width: `${barWidth((c.cumulative_time_ms / h.cumulative_time_ms) * 100)}%`
                          }"
                        />
                      </span>
                      <span class="profiling-hotspots-table__edge-time">
                        {{ formatMs(c.cumulative_time_ms) }}
                      </span>
                      <span class="profiling-hotspots-table__edge-count">
                        <!-- eslint-disable-next-line vue/no-bare-strings-in-template -- single-word count unit -->
                        {{ formatCalls(c.ncalls, c.primitive_calls) }} {{ _t('calls') }}
                      </span>
                    </div>
                  </div>
                </CmkCatalogPanel>
              </template>
            </div>
          </td>
        </tr>
      </tbody>
      <tbody v-if="paddingBottom > 0" class="profiling-hotspots-table__spacer" aria-hidden="true">
        <tr>
          <td :colspan="7" :style="{ height: `${paddingBottom}px` }"></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.profiling-hotspots-table {
  /* Fill remaining flex space, but shrink to content. Scrolls internally when
   * there are more rows than fit — no page scrollbar. */
  flex: 0 1 auto;
  min-height: 0;
  max-height: 100%;
  overflow: auto;
}

.profiling-hotspots-table__table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--font-size-normal);
  font-family: inherit;
}

/* Virtualization spacers stand in for the rows scrolled out of the DOM. */
.profiling-hotspots-table__spacer td {
  padding: 0;
  border: 0;
}

.profiling-hotspots-table__table th {
  text-align: left;
  padding: var(--spacing-half) var(--spacing);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  border-bottom: var(--border-width-1) solid var(--default-form-element-border-color);
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: var(--ux-theme-2);
  z-index: 1;
  user-select: none;
}

.profiling-hotspots-table__sort-btn {
  all: unset;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: color 0.15s;
  white-space: nowrap;
}

.profiling-hotspots-table__sort-btn:hover,
.profiling-hotspots-table__sort-btn:focus-visible {
  color: var(--font-color);
}

.profiling-hotspots-table__sort-btn:focus-visible {
  outline: var(--border-width-1) solid var(--color-dark-blue-50);
  outline-offset: var(--spacing-half);
}

/* Bar column headers: left-align at the ms-value position to match the data. */
.profiling-hotspots-table__table th.profiling-hotspots-table__col-bar {
  text-align: left;
}

/* SR-only label for the expand column. */
.profiling-hotspots-table__visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

.profiling-hotspots-table__table td {
  padding: var(--spacing-half) var(--spacing);
  vertical-align: middle;
  border-bottom: var(--border-width-1) solid var(--ux-theme-4);
}

.profiling-hotspots-table__row {
  cursor: pointer;
  transition: background 0.15s;
}

.profiling-hotspots-table__row:hover,
.profiling-hotspots-table__row:focus-visible {
  background: var(--ux-theme-4);
}

.profiling-hotspots-table__row:focus-visible {
  outline: var(--border-width-1) solid var(--color-dark-blue-50);
  outline-offset: calc(-1 * var(--border-width-1));
}

.profiling-hotspots-table__row.profiling-hotspots-table__row--highlighted {
  background: var(--ux-theme-5);
}

.profiling-hotspots-table__col-rank {
  width: var(--spacing-double);
}

.profiling-hotspots-table__col-function {
  min-width: 200px;
}

.profiling-hotspots-table__col-bar {
  min-width: 220px;
  width: 22%;
}

.profiling-hotspots-table__col-percall {
  width: 90px;
  text-align: right;
  font-family: monospace;
  font-size: var(--font-size-normal);
}

.profiling-hotspots-table__col-calls {
  width: 90px;
  text-align: right;
  font-family: monospace;
  font-size: var(--font-size-normal);
}

.profiling-hotspots-table__col-toggle {
  width: var(--spacing-double);
  text-align: center;
}

/* Rank cell with heat indicator */
.profiling-hotspots-table__rank-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
}

.profiling-hotspots-table__heat-bar {
  display: inline-block;

  /* Half of --spacing-half — no matching design-system token yet. */
  width: calc(var(--spacing-half) / 2);
  height: var(--spacing);
  border-radius: var(--border-radius-half);
}

.profiling-hotspots-table__rank-number {
  font-weight: var(--font-weight-bold);
}

/* Function name + file subtitle */
.profiling-hotspots-table__fn-name {
  font-weight: var(--font-weight-bold);
}

.profiling-hotspots-table__fn-file {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  margin-top: var(--spacing-half);
}

.profiling-hotspots-table__bar-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
}

.profiling-hotspots-table__bar-value {
  flex: 0 0 auto;
  width: 70px;
  text-align: right;
  font-family: monospace;
  font-size: var(--font-size-normal);
}

.profiling-hotspots-table__bar-track {
  flex: 1;
  height: var(--spacing);
  background: var(--ux-theme-4);
  border-radius: var(--border-radius-half);
  min-width: 80px;
  overflow: hidden;
}

.profiling-hotspots-table__bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--border-radius-half);
  transition: width 0.2s ease;
}

.profiling-hotspots-table__bar-pct {
  flex: 0 0 auto;
  width: 50px;
  font-family: monospace;
  font-size: var(--font-size-normal);
}

.profiling-hotspots-table__toggle-btn {
  transition: transform 0.15s;
}

.profiling-hotspots-table__toggle-btn.profiling-hotspots-table__toggle-btn--open {
  transform: rotate(90deg);
}

.profiling-hotspots-table__detail-row td {
  padding: 0 var(--spacing) var(--spacing);
  border-bottom: var(--border-width-1) solid var(--ux-theme-5);
}

.profiling-hotspots-table__detail-panel {
  display: flex;
  gap: var(--spacing-double);
  padding: var(--spacing) 0;
  font-size: var(--font-size-normal);
}

.profiling-hotspots-table__detail-card {
  flex: 1;
  min-width: 0;
}

.profiling-hotspots-table__edge-item {
  padding: var(--spacing-half) 0;
}

.profiling-hotspots-table__edge-item + .profiling-hotspots-table__edge-item {
  border-top: var(--border-width-1) solid var(--ux-theme-5);
}

.profiling-hotspots-table__edge-item--clickable {
  cursor: pointer;
  padding: var(--spacing-half);
  border-radius: var(--border-radius);
  transition: background 0.15s;
}

.profiling-hotspots-table__edge-item--clickable:hover,
.profiling-hotspots-table__edge-item--clickable:focus-visible {
  background: var(--ux-theme-4);
}

.profiling-hotspots-table__edge-item--clickable:focus-visible {
  outline: var(--border-width-1) solid var(--color-dark-blue-50);
  outline-offset: calc(-1 * var(--border-width-1));
}

.profiling-hotspots-table__edge-main {
  margin-bottom: var(--spacing-half);
}

.profiling-hotspots-table__edge-fn {
  font-family: monospace;
  font-size: var(--font-size-normal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profiling-hotspots-table__edge-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.profiling-hotspots-table__edge-bar-track {
  flex: 1;
  height: var(--spacing-half);
  background: var(--ux-theme-5);
  border-radius: var(--border-radius-half);
  min-width: 40px;
  max-width: 120px;
  overflow: hidden;
}

.profiling-hotspots-table__edge-bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--border-radius-half);
  background: var(--font-color-dimmed);
  transition: width 0.2s ease;
}

.profiling-hotspots-table__edge-count {
  flex: 0 0 auto;
  white-space: nowrap;
}

.profiling-hotspots-table__edge-time {
  flex: 0 0 auto;
  white-space: nowrap;
  font-family: monospace;
}
</style>
