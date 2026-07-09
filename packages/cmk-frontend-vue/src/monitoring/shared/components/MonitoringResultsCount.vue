<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import usei18n from '@/lib/i18n'

import { MONITORING_SERVICE } from './MonitoringTableContext'

const { _t } = usei18n()

const monitoringService = inject(MONITORING_SERVICE)

const visible = computed(() => (monitoringService?.matched.value ?? 0) > 0)

const label = computed(() => {
  const count = monitoringService?.matched.value ?? 0
  const total = monitoringService?.total.value ?? 0
  const hasSearch = (monitoringService?.committedSearchQuery.value ?? '') !== ''
  const filterCount = monitoringService?.filters.activeFilterCount ?? 0
  if (filterCount > 0 || hasSearch) {
    return _t('Rows matching your criteria: %{count} | Total rows: %{total}', { count, total })
  }
  return _t('Total rows: %{total}', { total })
})
</script>

<template>
  <p class="monitoring-results-count" aria-live="polite">{{ visible ? label : '\xa0' }}</p>
</template>

<style scoped>
.monitoring-results-count {
  margin: 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
