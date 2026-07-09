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

const hasSearchQuery = computed(() => (monitoringService?.searchQuery.value ?? '') !== '')
const hasActiveFilter = computed(() => (monitoringService?.filters.activeFilterCount ?? 0) > 0)

const title = computed(() => {
  if (hasActiveFilter.value && hasSearchQuery.value) {
    return _t('No results for your combination of search and filter settings.')
  }
  if (hasActiveFilter.value) {
    return _t('No results found for your active filters.')
  }
  if (hasSearchQuery.value) {
    return _t('No results found for your search.')
  }
  return _t('No results found.')
})

const hint = computed(() => {
  if (hasActiveFilter.value && hasSearchQuery.value) {
    return _t('Adjust or clear search and filters to start fresh.')
  }
  if (hasSearchQuery.value) {
    return _t('Check for typing errors or try a broader term.')
  }
  return null
})
</script>

<template>
  <div class="monitoring-empty-state" aria-live="polite">
    <p class="monitoring-empty-state__title">{{ title }}</p>
    <p v-if="hint" class="monitoring-empty-state__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.monitoring-empty-state {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  padding: var(--spacing) var(--spacing-half);
}

.monitoring-empty-state__title {
  margin: 0;
  font-weight: var(--font-weight-bold);
}

.monitoring-empty-state__hint {
  margin: 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
