<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import { MONITORING_SERVICE } from './MonitoringTableContext'

const { _t } = usei18n()

const monitoringService = inject(MONITORING_SERVICE)

// Hidden during a foreground fetch so it does not linger with stale numbers after a limit change.
const truncated = computed(
  () =>
    (monitoringService?.resultsTruncated.value ?? false) &&
    monitoringService?.fetchState.value !== 'foreground'
)

const canRaiseLimit = computed(() => monitoringService?.canRaiseLimit.value ?? false)

const narrowed = computed(
  () =>
    (monitoringService?.filters.activeFilterCount ?? 0) > 0 ||
    (monitoringService?.committedSearchQuery.value ?? '') !== ''
)

const message = computed(() => {
  const limit = monitoringService?.limit.value ?? 0
  const matched = monitoringService?.matched.value ?? 0
  if (narrowed.value) {
    return canRaiseLimit.value
      ? _t(
          'Showing %{limit} of %{matched} matching hosts. Narrow your search, or raise the row limit above.',
          { limit, matched }
        )
      : _t('Showing %{limit} of %{matched} matching hosts. Narrow your search to see the rest.', {
          limit,
          matched
        })
  }
  return canRaiseLimit.value
    ? _t(
        'Showing %{limit} of %{matched} hosts. Narrow your search, or raise the row limit above.',
        { limit, matched }
      )
    : _t('Showing %{limit} of %{matched} hosts. Narrow your search to see the rest.', {
        limit,
        matched
      })
})

const caveat = _t(
  "The row limit is applied before sorting, so the hidden rows aren't necessarily the lowest-ranked. Narrow your search for a complete, sorted list."
)

const infoIconColor = { custom: 'var(--cmk-alert-box-info-icon-color)' }
</script>

<template>
  <p v-if="truncated" class="monitoring-truncation-notice" role="status" aria-live="polite">
    <CmkMultitoneIcon
      name="help"
      :primary-color="infoIconColor"
      size="small"
      class="monitoring-truncation-notice__icon"
    />
    <span>{{ message }}</span>
    <CmkHelpText :help="caveat" />
  </p>
</template>

<style scoped>
.monitoring-truncation-notice {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  margin: 0;
  color: var(--font-color);
  font-size: var(--font-size-small);
}

.monitoring-truncation-notice__icon {
  flex: 0 0 auto;
}
</style>
