<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import { MONITORING_SERVICE } from './MonitoringTableContext'

const { _t } = usei18n()

const props = defineProps<{
  /**
   * What the counted rows are, appended to the range label ("1-500 of 1 247 302
   * flows"). Omit for a bare count.
   */
  unit?: string
}>()

const monitoringService = inject(MONITORING_SERVICE)

const first = computed(() => monitoringService?.pageFirst.value ?? 0)
const last = computed(() => monitoringService?.pageLast.value ?? 0)
const matched = computed(() => monitoringService?.matched.value ?? 0)

const hasPrevious = computed(() => monitoringService?.hasPreviousPage.value ?? false)
const hasNext = computed(() => monitoringService?.hasNextPage.value ?? false)

// Only worth rendering once there is a page to move to. A single-page listing
// already states its size through the total count next to it.
const visible = computed(() => hasPrevious.value || hasNext.value)

// Exact positions, so the SI formatter is deliberately not used here - it would
// render row 1000 as "1 k". The total is a position too, and reads consistently
// with the bounds when it is grouped the same way.
const numberFormat = new Intl.NumberFormat()

const label = computed(() => {
  const range = {
    first: numberFormat.format(first.value),
    last: numberFormat.format(last.value),
    total: numberFormat.format(matched.value)
  }
  return props.unit === undefined
    ? _t('%{first}-%{last} of %{total}', range)
    : _t('%{first}-%{last} of %{total} %{unit}', { ...range, unit: props.unit })
})
</script>

<template>
  <nav v-if="visible" class="monitoring-pagination" :aria-label="_t('Pages')">
    <p class="monitoring-pagination__label" aria-live="polite">{{ label }}</p>
    <CmkButton
      variant="optional"
      class="monitoring-pagination__nav"
      :title="_t('Previous page')"
      :aria-label="_t('Previous page')"
      :disabled="!hasPrevious"
      @click="monitoringService?.previousPage()"
    >
      <CmkIcon name="back" size="small" />
    </CmkButton>
    <CmkButton
      variant="optional"
      class="monitoring-pagination__nav"
      :title="_t('Next page')"
      :aria-label="_t('Next page')"
      :disabled="!hasNext"
      @click="monitoringService?.nextPage()"
    >
      <CmkIcon name="continue" size="small" />
    </CmkButton>
  </nav>
</template>

<style scoped>
.monitoring-pagination {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  white-space: nowrap;
}

.monitoring-pagination__label {
  margin: 0;
}
</style>
