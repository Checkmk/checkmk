<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import type { RequestedLimit } from '@/monitoring/shared/types'

import { MONITORING_SERVICE } from './MonitoringTableContext'

const { _t } = usei18n()

const monitoringService = inject(MONITORING_SERVICE)

const UNLIMITED_NAME = 'all'

function toName(limit: RequestedLimit): string {
  return limit === null ? UNLIMITED_NAME : String(limit)
}

const hasChoice = computed(() => (monitoringService?.offeredLimits.length ?? 0) > 1)

const options = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: (monitoringService?.offeredLimits ?? []).map((limit) => ({
    name: toName(limit),
    title: limit === null ? _t('All') : untranslated(String(limit))
  }))
}))

const selected = computed<string | null>({
  get: () => (monitoringService ? toName(monitoringService.requestedLimit.value) : null),
  set: (name) => {
    if (name === null) {
      return
    }
    monitoringService?.setRequestedLimit(name === UNLIMITED_NAME ? null : Number(name))
  }
})
</script>

<template>
  <div v-if="hasChoice" class="monitoring-limit-selector">
    <span class="monitoring-limit-selector__label">{{ _t('Show:') }}</span>
    <CmkDropdown v-model="selected" :options="options" :label="_t('Row limit')" />
  </div>
</template>

<style scoped>
.monitoring-limit-selector {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  white-space: nowrap;
}
</style>
