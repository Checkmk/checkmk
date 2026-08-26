<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import CmkDeltaArrow from '@/dashboard/components/CmkDeltaArrow.vue'
import GraphLegendEyeButton from '@/graphing/components/legend/GraphLegendEyeButton.vue'

import { chartColorCss } from '../colors'
import type { DonutLegendRow } from './types'

const { _t } = usei18n()

const props = defineProps<{
  rows: DonutLegendRow[]
  highlighted: string | null
  /** Names the window the comparison is against; falls back to a bare label. */
  previousLabel?: string | undefined
  /** Whether the widget is wide enough to carry the comparison columns. */
  showComparison: boolean
}>()

defineEmits<{
  toggle: [key: string]
  highlight: [key: string | null]
  drill: [key: string]
}>()

// Decided over the whole legend, not per row: a header that comes and goes with
// the row under the pointer is worse than one column of dashes.
const hasPrevious = computed(() => props.rows.some((row) => row.previousText !== null))

// The chart measures, because the answer also settles how much width the ring
// may have.
const comparisonVisible = computed(() => hasPrevious.value && props.showComparison)
const comparisonWithheld = computed(() => hasPrevious.value && !props.showComparison)

const withheldHint = computed(() =>
  _t('%{previous} and %{change} are hidden: the widget is too narrow to carry them.', {
    previous: props.previousLabel ?? _t('Previous'),
    change: _t('Change')
  })
)

/** Which way a row's arrow points, or null for a change that has no direction. */
function deltaDirection(row: DonutLegendRow): 'up' | 'down' | null {
  const ratio = row.delta?.ratio ?? null
  if (ratio === null || ratio === 0) {
    return null
  }
  return ratio > 0 ? 'up' : 'down'
}
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
          <!-- Also on the cell, because contextual help renders nothing at all
               for a user who has turned the help icons off. -->
          <th
            class="network-flow-donut-legend-table__th"
            :title="comparisonWithheld ? withheldHint : undefined"
          >
            <span class="network-flow-donut-legend-table__th-content">
              {{ _t('Category') }}
              <CmkHelpText
                v-if="comparisonWithheld"
                :help="withheldHint"
                :aria-label="_t('Why the comparison is not shown')"
                use-portal
              />
            </span>
          </th>
          <th
            class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value"
          >
            {{ _t('Current') }}
          </th>
          <template v-if="comparisonVisible">
            <th
              class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value network-flow-donut-legend-table__th--comparison"
            >
              {{ previousLabel ?? _t('Previous') }}
            </th>
            <th
              class="network-flow-donut-legend-table__th network-flow-donut-legend-table__th--value network-flow-donut-legend-table__th--change"
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
          <template v-if="comparisonVisible">
            <td
              class="network-flow-donut-legend-table__td network-flow-donut-legend-table__td--value network-flow-donut-legend-table__td--comparison"
            >
              {{ row.previousText }}
            </td>
            <td
              class="network-flow-donut-legend-table__td network-flow-donut-legend-table__td--value network-flow-donut-legend-table__td--change"
            >
              <span class="network-flow-donut-legend-table__delta">
                <CmkDeltaArrow
                  v-if="deltaDirection(row) !== null"
                  :direction="deltaDirection(row)!"
                />
                {{ row.delta?.text }}
              </span>
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
  padding: 0.45em 0.55em;
  font-size: 0.85em;
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
  text-align: left;
  letter-spacing: 0.04em;

  /* Ellipsis rather than stopping mid-glyph, where "Prev 30 min" read as
     "Prev 30 mir". */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  /* Opaque, or the rows scroll through the header. */
  background-color: var(--db-content-bg-color);

  /* An inset shadow rather than a border: collapsed borders are painted by the
     table, so a border on a sticky cell scrolls away with the rows. */
  box-shadow: inset 0 -1px 0 var(--ux-theme-6);
}

/* Wrapped, because a th laid out as a flex container is no longer a table
   cell, and the fixed column widths go with it. */
.network-flow-donut-legend-table__th-content {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  vertical-align: middle;
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

/* Headed by the window it is against ("Prev 30 min"), which needs more room
   than the figures under it. */
.network-flow-donut-legend-table__th--comparison,
.network-flow-donut-legend-table__td--comparison {
  width: 6.5em;
}

/* An arrow and a percentage; narrower than a formatted volume. */
.network-flow-donut-legend-table__th--change,
.network-flow-donut-legend-table__td--change {
  width: 4.5em;
}

.network-flow-donut-legend-table__td {
  /* In em, so the rows get shorter as the text does. */
  padding: 0.45em 0.55em;

  /* The fixed layout hands the category cell whatever the numbers leave, and
     this is what makes the name give way inside it. */
  overflow: hidden;
  border-bottom: 1px solid var(--ux-theme-6);
}

/* The arrow rides along the end of the figure rather than taking a column of
   its own, so the numbers stay in one right-aligned stack. */
.network-flow-donut-legend-table__delta {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  justify-content: flex-end;
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
