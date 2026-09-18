<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useTemplateRef } from 'vue'

import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

const props = defineProps<{
  service: MonitoringService<T>
  searchPlaceholder: TranslatedString
}>()

const { _t } = usei18n()

const searchQuery = props.service.searchQuery

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

defineExpose({
  focus: (): void => searchInput.value?.focus()
})
</script>

<template>
  <div class="monitoring-toolbar">
    <div v-if="$slots.subject" class="monitoring-toolbar__subject">
      <slot name="subject" />
    </div>
    <div class="monitoring-toolbar__controls">
      <div class="monitoring-toolbar__filters">
        <CmkSearchInput
          ref="searchInput"
          v-model="searchQuery"
          class="monitoring-toolbar__search"
          :placeholder="searchPlaceholder"
          @search="service.updateSearch($event)"
          @focusin="service.beginAutoPause()"
          @focusout="service.endAutoPause()"
        />
        <div class="monitoring-toolbar__quick-filters">
          <QuickFilterChip
            v-for="chip in service.filters.quickFilters"
            :key="chip.label"
            :label="chip.label"
            :tooltip="chip.tooltip"
            :active="chip.isActive.value"
            @activate="service.activateQuickFilter(chip)"
            @deactivate="service.deactivateQuickFilter(chip)"
          />
        </div>
        <CmkButton variant="text" size="small" @click="service.clearAllFilters()">
          {{ _t('Reset all filters') }}
        </CmkButton>
      </div>
      <div class="monitoring-toolbar__end">
        <RefreshCountdown
          :remaining="service.secondsRemaining.value"
          :interval="service.pollIntervalSeconds"
          :paused="service.paused.value"
          :manual-paused="service.manualPaused.value"
          size="small"
          @toggle="service.togglePause()"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-toolbar {
  --monitoring-toolbar-border-color: var(--color-mid-grey-10);

  box-sizing: border-box;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--ux-theme-2);
  border-bottom: 1px solid var(--monitoring-toolbar-border-color);
}

body[data-theme='modern-dark'] .monitoring-toolbar {
  --monitoring-toolbar-border-color: var(--color-mid-grey-100);
}

.monitoring-toolbar__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.monitoring-toolbar__filters {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-toolbar__end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-toolbar__search {
  flex: 1;
  max-width: 360px;
}

.monitoring-toolbar__quick-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}
</style>
