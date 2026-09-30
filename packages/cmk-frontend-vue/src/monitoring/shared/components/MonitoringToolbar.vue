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
        <CmkButton
          variant="text"
          size="small"
          class="monitoring-toolbar__reset"
          @click="service.clearAllFilters()"
        >
          {{ _t('Reset search and filters') }}
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

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;
@use './monitoringLayout' as layout;

.monitoring-toolbar {
  box-sizing: border-box;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--ux-theme-2);
  border-bottom: 1px solid var(--sticky-header-border-color);

  /* The filter row below reflows with the width of the toolbar. */
  container-type: inline-size;

  /* Narrower than this the app root scrolls horizontally instead of the countdown overlapping
     the search. */
  min-width: layout.$min-content-width;
}

.monitoring-toolbar__controls {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing);
}

.monitoring-toolbar__filters {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  min-width: 0;
  gap: var(--spacing);
}

.monitoring-toolbar__end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  /* Keeps the countdown level with the search input, however many rows the filters wrap to. */
  min-height: layout.$search-input-height;
  gap: var(--spacing);
}

.monitoring-toolbar__search {
  flex: 0 1 360px;
  /* Keeps the search field and its button usable when the filter row gets squeezed. */
  min-width: 10em;
}

.monitoring-toolbar__reset {
  white-space: nowrap;
}

.monitoring-toolbar__quick-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
  white-space: nowrap;
}

/* Narrower than M: the quick filters and the reset button move below the search, which keeps
   its width (an empty full-width item forces the line break). Narrower than S: the reset
   button moves below the filters. */
@include bp.container-below(m) {
  .monitoring-toolbar__filters::before {
    content: '';
    order: 1;
    flex-basis: 100%;
    height: 0;
  }

  .monitoring-toolbar__quick-filters,
  .monitoring-toolbar__reset {
    order: 2;
  }
}

@include bp.container-below(s) {
  .monitoring-toolbar__quick-filters {
    flex-basis: 100%;
  }
}
</style>
