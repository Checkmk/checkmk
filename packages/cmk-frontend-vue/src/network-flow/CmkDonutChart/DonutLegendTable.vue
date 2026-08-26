<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import GraphLegendEyeButton from '@/graphing/components/legend/GraphLegendEyeButton.vue'

import { chartColorCss } from '../colors'
import type { DonutLegendRow } from './types'

const { _t } = usei18n()

const props = defineProps<{
  rows: DonutLegendRow[]
  highlighted: string | null
  /** Names the window the comparison is against; falls back to a bare label. */
  previousLabel?: string | undefined
}>()

defineEmits<{
  toggle: [key: string]
  highlight: [key: string | null]
  drill: [key: string]
}>()

// Decided over the whole legend, not per row: a header that comes and goes with
// the row under the pointer is worse than one column of dashes.
const hasPrevious = computed(() => props.rows.some((row) => row.previousText !== null))
</script>

<template>
  <!-- One table rather than a header and a body of their own: the name column is
       fluid, and two tables would resolve it against two different widths. -->
  <CmkScrollContainer
    class="network-flow-donut-legend-table"
    max-height="100%"
    height="auto"
    :style="{ overflowX: 'hidden' }"
  >
    <table class="network-flow-donut-legend-table__table">
      <thead>
        <tr>
          <th class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--eye">
            <span class="network-flow-donut-legend-table__visually-hidden">
              {{ _t('Visible') }}
            </span>
          </th>
          <th class="network-flow-donut-legend-table__th">{{ _t('Category') }}</th>
          <th
            class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value"
          >
            {{ _t('Current') }}
          </th>
          <template v-if="hasPrevious">
            <th
              class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value network-flow-donut-legend-table__th--comparison"
            >
              {{ previousLabel ?? _t('Previous') }}
            </th>
            <th
              class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value network-flow-donut-legend-table__th--comparison"
            >
              {{ _t('Change') }}
            </th>
          </template>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.key"
          class="network-flow-donut-legend-table__row"
          :class="{
            'network-flow-donut-legend-table__row--highlighted': highlighted === row.key,
            'network-flow-donut-legend-table__row--hidden': row.hidden
          }"
          @mouseenter="$emit('highlight', row.key)"
          @mouseleave="$emit('highlight', null)"
        >
          <td class="network-flow-donut-legend-table__td">
            <GraphLegendEyeButton
              :hidden="row.hidden"
              :aria-label="
                row.hidden
                  ? _t('Show %{category} in the chart', { category: row.label })
                  : _t('Hide %{category} in the chart', { category: row.label })
              "
              @toggle="$emit('toggle', row.key)"
            />
          </td>
          <td class="network-flow-donut-legend-table__td">
            <span class="network-flow-donut-legend-table__category">
              <span
                class="network-flow-donut-legend-table__swatch"
                :style="{ backgroundColor: row.hidden ? '' : chartColorCss(row.color) }"
              />
              <!-- The remainder is the one row with something behind it, and
                   only while it is part of the ring: drilling into a category
                   the reader just hid would open the very thing they closed.
                   The name is part of the control rather than sitting beside
                   it, so the row reads as one target instead of asking the
                   reader to find a chevron. -->
              <CmkButton
                v-if="row.isOther && !row.hidden"
                variant="text"
                size="small"
                class="network-flow-donut-legend-table__drill"
                :aria-label="_t('Show breakdown of %{category}', { category: row.label })"
                @click="$emit('drill', row.key)"
              >
                <!-- Truncated on the name, so the chevron keeps its place. -->
                <span class="network-flow-donut-legend-table__label" :title="row.label">
                  {{ row.label }}
                </span>
                <CmkMultitoneIcon
                  class="network-flow-donut-legend-table__chevron"
                  name="chevron-right"
                  primary-color="font"
                  size="small"
                />
              </CmkButton>
              <span v-else class="network-flow-donut-legend-table__label" :title="row.label">
                {{ row.label }}
              </span>
            </span>
          </td>
          <td
            class="network-flow-donut-legend-table__td network-flow-donut-legend-table__td--value"
          >
            {{ row.currentText }}
          </td>
          <template v-if="hasPrevious">
            <td
              class="network-flow-donut-legend-table__td network-flow-donut-legend-table__td--value network-flow-donut-legend-table__td--comparison"
            >
              {{ row.previousText }}
            </td>
            <td
              class="network-flow-donut-legend-table__td network-flow-donut-legend-table__td--value network-flow-donut-legend-table__td--comparison"
            >
              {{ row.deltaText }}
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </CmkScrollContainer>
</template>

<style scoped>
/* Sized off the chart's container query, so no container of its own here. */
.network-flow-donut-legend-table {
  flex: 1;
  min-width: 0;
}

.network-flow-donut-legend-table__table {
  width: 100%;
  border-collapse: collapse;

  /* Fixed, so a value column can never push the table past the widget: the
     category column absorbs the shortfall and its name truncates instead. */
  table-layout: fixed;
}

/* On the cells, not on thead, which does not stick reliably. */
.network-flow-donut-legend-table__th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: clamp(2px, 1.5cqh, 7px) clamp(2px, 1cqw, 8px);
  font-size: 0.85em;
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
  text-align: left;
  letter-spacing: 0.04em;
  white-space: nowrap;

  /* Opaque, or the rows scroll through the header. */
  background-color: var(--db-content-bg-color);

  /* An inset shadow rather than a border: collapsed borders are painted by the
     table, so a border on a sticky cell scrolls away with the rows. */
  box-shadow: inset 0 -1px 0 var(--ux-theme-6);
}

.network-flow-donut-legend-table__th--eye {
  /* The eye button is a hard 20x20 and does not scale with the text. */
  width: 20px;
}

.network-flow-donut-legend-table__th--value,
.network-flow-donut-legend-table__td--value {
  /* Wide enough for a formatted volume, and em-relative so the column tracks
     the text as the widget shrinks. */
  width: 5.5em;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

/* Past a certain narrowness three numbers per row leave the category names a
   few characters each. The comparison is what goes: what is flowing now is the
   column nobody can do without. */
@container nf-donut (width < 430px) {
  .network-flow-donut-legend-table__th--comparison,
  .network-flow-donut-legend-table__td--comparison {
    display: none;
  }
}

.network-flow-donut-legend-table__td {
  padding: clamp(2px, 1.5cqh, 7px) clamp(2px, 1cqw, 8px);

  /* The fixed layout hands the category cell whatever the numbers leave, and
     this is what makes the name give way inside it. */
  overflow: hidden;
  border-bottom: 1px solid var(--ux-theme-6);
}

.network-flow-donut-legend-table__row--highlighted {
  background-color: var(--ux-theme-4);
}

/* A hidden category keeps its row, so it stays reachable. */
.network-flow-donut-legend-table__row--hidden {
  opacity: 0.45;
}

.network-flow-donut-legend-table__category {
  display: flex;
  gap: clamp(4px, 1cqw, 10px);
  align-items: center;
  min-width: 0;
}

/* A bar rather than a square, and em-relative so it tracks the row's text. */
.network-flow-donut-legend-table__swatch {
  flex: 0 0 auto;
  width: 0.3em;
  min-width: 3px;
  height: 1.1em;
  border-radius: var(--border-radius-half);
}

.network-flow-donut-legend-table__row--hidden .network-flow-donut-legend-table__swatch {
  background-color: var(--color-mid-grey-30);
}

.network-flow-donut-legend-table__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* The button sizes itself for a form; in a legend row it has to sit in the
   line the other categories sit in, and give way at the name like they do. */
.network-flow-donut-legend-table__drill {
  gap: inherit;
  justify-content: flex-start;
  min-width: 0;
  height: auto;
  padding: 0;
  font: inherit;
  text-align: left;
}

.network-flow-donut-legend-table__chevron {
  flex: 0 0 auto;
}

.network-flow-donut-legend-table__visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
