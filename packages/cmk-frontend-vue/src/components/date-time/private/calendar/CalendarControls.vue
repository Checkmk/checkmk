<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton'
import CmkDropdown from '@/components/CmkDropdown'
import { type Suggestions } from '@/components/CmkSuggestions'
import ArrowDown from '@/components/graphics/ArrowDown.vue'

const props = withDefaults(
  defineProps<{
    /** Displayed month, 1-12. */
    month: number
    /** Displayed year. */
    year: number
    /** Short month names shown in the month dropdown. */
    monthNamesDisplay: TranslatedString[]
    /** Show the "previous month" button. */
    showPrev?: boolean
    /** Show the "next month" button. */
    showNext?: boolean
    /** Show the month dropdown. */
    showMonthDropdown?: boolean
    /** Show the year dropdown. */
    showYearDropdown?: boolean
    /** `[from, to]` span listed by the year dropdown. */
    yearRange: [number, number]
  }>(),
  {
    showPrev: true,
    showNext: true,
    showMonthDropdown: true,
    showYearDropdown: true
  }
)

const emit = defineEmits<{
  /** The "previous month" button was pressed. */
  (e: 'prev'): void
  /** The "next month" button was pressed. */
  (e: 'next'): void
  /** A month was chosen in the dropdown (1-12). */
  (e: 'update:month', value: number): void
  /** A year was chosen in the dropdown. */
  (e: 'update:year', value: number): void
}>()

const { _t } = usei18n()

const monthOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: props.monthNamesDisplay.map((name, index) => ({ name: `${index + 1}`, title: name }))
}))

const yearOptions = computed<Suggestions>(() => {
  // Always include the displayed year so a year reached via the prev/next buttons (which are not
  // bounded by `yearRange`) still renders as the selected option. Newest year first.
  const from = Math.min(props.yearRange[0], props.year)
  const to = Math.max(props.yearRange[1], props.year)
  const years = Array.from({ length: to - from + 1 }, (_unused, index) => to - index)
  return {
    type: 'fixed',
    suggestions: years.map((value) => ({ name: `${value}`, title: untranslated(`${value}`) }))
  }
})

function onMonthUpdate(value: string | null): void {
  if (value !== null) {
    emit('update:month', parseInt(value, 10))
  }
}

function onYearUpdate(value: string | null): void {
  if (value !== null) {
    emit('update:year', parseInt(value, 10))
  }
}
</script>

<template>
  <div class="cmk-calendar-controls">
    <CmkButton
      class="cmk-calendar-controls__nav"
      :class="{ 'cmk-calendar-controls__nav--hidden': !showPrev }"
      variant="optional"
      :title="_t('Previous month')"
      :aria-label="_t('Previous month')"
      :disabled="!showPrev"
      @click="emit('prev')"
    >
      <ArrowDown class="cmk-calendar-controls__nav-icon cmk-calendar-controls__nav-icon--prev" />
    </CmkButton>

    <div class="cmk-calendar-controls__dropdowns">
      <CmkDropdown
        v-if="showMonthDropdown"
        :model-value="`${month}`"
        :options="monthOptions"
        :label="_t('Month')"
        @update:model-value="onMonthUpdate"
      />
      <CmkDropdown
        v-if="showYearDropdown"
        :model-value="`${year}`"
        :options="yearOptions"
        :label="_t('Year')"
        @update:model-value="onYearUpdate"
      />
    </div>

    <CmkButton
      class="cmk-calendar-controls__nav"
      :class="{ 'cmk-calendar-controls__nav--hidden': !showNext }"
      variant="optional"
      :title="_t('Next month')"
      :aria-label="_t('Next month')"
      :disabled="!showNext"
      @click="emit('next')"
    >
      <ArrowDown class="cmk-calendar-controls__nav-icon cmk-calendar-controls__nav-icon--next" />
    </CmkButton>
  </div>
</template>

<style scoped>
.cmk-calendar-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-3);
}

.cmk-calendar-controls__dropdowns {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.cmk-calendar-controls__nav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-7);
  height: var(--dimension-7);
  padding: 0;
}

.cmk-calendar-controls__nav--hidden {
  visibility: hidden;
}

.cmk-calendar-controls__nav-icon {
  flex-shrink: 0;
  width: 0.7em;
}

.cmk-calendar-controls__nav-icon--prev {
  transform: rotate(90deg);
}

.cmk-calendar-controls__nav-icon--next {
  transform: rotate(-90deg);
}
</style>
