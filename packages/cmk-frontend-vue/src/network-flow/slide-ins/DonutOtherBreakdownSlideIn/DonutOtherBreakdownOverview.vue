<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import type { NetworkFlowDonutContent } from '@/dashboard/types/widget'
import { CHART_COLOR_CSS } from '@/network-flow/colors'
import { formatBytes, formatDelta } from '@/network-flow/format'

import type { ComputedNetworkFlowDonutOtherBreakdown } from '../api/context'

const { _t, _tn } = usei18n()

const props = defineProps<{
  data: ComputedNetworkFlowDonutOtherBreakdown
  previousLabel?: string | undefined
}>()

const breakdown = computed(() => props.data)

type Dimension = NetworkFlowDonutContent['dimension']

// Keyed by the dimension rather than tested for one, so a third dimension is a
// build failure instead of a panel labelled "application" by default.
const COLUMN_TITLE: Record<Dimension, () => string> = {
  applications: () => _t('Application'),
  protocols: () => _t('Protocol')
}

const CATEGORY_COUNT: Record<Dimension, (count: number) => string> = {
  applications: (count) =>
    _tn('%{count} application', '%{count} applications', count, { count: `${count}` }),
  protocols: (count) => _tn('%{count} protocol', '%{count} protocols', count, { count: `${count}` })
}

const summary = computed(() =>
  CATEGORY_COUNT[breakdown.value.dimension](breakdown.value.category_count)
)

// Absent when no comparison was asked for; zero when the widget asked and the
// preceding window held nothing, which would report every category as new.
const hasHistory = computed(
  () => breakdown.value.previous_total !== undefined && breakdown.value.previous_total > 0
)

const columns = computed<RankedTableColumn[]>(() => {
  const dimensionColumn: RankedTableColumn = {
    key: 'label',
    title: COLUMN_TITLE[breakdown.value.dimension](),
    render: 'text',
    bar: false
  }
  const shareColumn: RankedTableColumn = {
    key: 'share',
    title: _t('Share'),
    render: 'text',
    bar: true,
    // Against the whole remainder: scaled to the largest row, the top category
    // would always read as a full bar.
    barRange: [0, 100]
  }
  const current: RankedTableColumn = {
    key: 'value',
    title: _t('Current'),
    render: 'bytes',
    bar: false
  }
  if (!hasHistory.value) {
    return [dimensionColumn, shareColumn, current]
  }
  return [
    dimensionColumn,
    shareColumn,
    current,
    {
      key: 'previous_value',
      title: props.previousLabel ?? _t('Previous'),
      render: 'bytes',
      bar: false
    },
    { key: 'delta', title: _t('Change'), render: 'count', bar: false }
  ]
})

const rows = computed<RankedTableRow[]>(() =>
  breakdown.value.categories.map((category) => ({
    label: category.label,
    share: { value: category.share, formatted: `${category.share.toFixed(1)}%` },
    value: category.value,
    // Both are read only while the comparison columns are shown, which is
    // exactly when the payload carries them.
    previous_value: category.previous_value ?? 0,
    delta: formatDelta(category.value, category.previous_value ?? 0)
  }))
)
// Derived rather than reported, so it cannot disagree with the list beside it.
const truncated = computed(() => rows.value.length < breakdown.value.category_count)
</script>

<template>
  <div class="network-flow-donut-other-breakdown-overview">
    <section>
      <dl class="network-flow-donut-other-breakdown-overview__metrics">
        <div>
          <dt>{{ _t('Behind the slice') }}</dt>
          <dd>{{ summary }}</dd>
        </div>
        <div>
          <dt>{{ _t('Other volume') }}</dt>
          <dd>{{ formatBytes(breakdown.total) }}</dd>
        </div>
      </dl>
    </section>

    <section>
      <CmkParagraph v-if="rows.length === 0">
        {{ _t('The ranked categories account for all traffic the ring measured.') }}
      </CmkParagraph>
      <CmkRankedTable v-else :columns="columns" :rows="rows" :bar-color="CHART_COLOR_CSS.grey" />
      <CmkParagraph v-if="truncated">
        {{
          _t('Showing the largest %{shown} of %{total}.', {
            shown: `${rows.length}`,
            total: summary
          })
        }}
      </CmkParagraph>
    </section>
  </div>
</template>

<style scoped>
.network-flow-donut-other-breakdown-overview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.network-flow-donut-other-breakdown-overview__metrics {
  display: flex;
  gap: var(--spacing-double);
  margin: 0;
}

.network-flow-donut-other-breakdown-overview__metrics dt {
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.network-flow-donut-other-breakdown-overview__metrics dd {
  margin: 0;
  font-size: 1.4em;
  font-variant-numeric: tabular-nums;
}
</style>
