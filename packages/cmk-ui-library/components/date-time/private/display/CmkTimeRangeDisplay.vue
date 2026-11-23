<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CalendarDate } from '@internationalized/date'
import CmkGhostWidth from 'cmk-ui-library/components/CmkGhostWidth.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import { formatDate, formatTime } from '../../dateTimeUtils'
import type { DateTimePartsDraft, ResolvedDateTimeSettings, TimeValue } from '../../types'

const props = defineProps<{
  /** Range start; each half is rendered as "—" while empty. */
  from: DateTimePartsDraft
  /** Range end; each half is rendered as "—" while empty. */
  to: DateTimePartsDraft
  /** Resolved display settings (from `useResolvedDateTimeSettings`), shared with the picker. */
  settings: ResolvedDateTimeSettings
}>()

const { _t } = usei18n()

/** The visible "—" of an empty half reads as "em dash"; give assistive tech a meaningful name. */
function emptyName(value: unknown): TranslatedString | undefined {
  return value === null ? _t('not set') : undefined
}

function dateText(date: CalendarDate | null): string {
  return date ? formatDate(date, props.settings.dateFormat) : '—'
}

function timeText(time: TimeValue | null): string {
  return time ? formatTime(time, props.settings.hourCycle) : '—'
}

// Reserve the width of the wider meridiem so AM ↔ PM never shifts the grid. The digit placeholder
// is as wide as any real time (tabular digits), so the value itself does not matter.
const timeWidthVariants = computed(() =>
  props.settings.hourCycle !== 24 ? ['00:00 AM', '00:00 PM'] : []
)
</script>

<template>
  <div class="cmk-time-range-display">
    <span>{{ _t('From') }}</span>
    <span :aria-label="emptyName(props.from.date)">
      <b>{{ dateText(props.from.date) }}</b>
    </span>
    <span class="cmk-time-range-display__divider" aria-hidden="true">{{ untranslated('|') }}</span>
    <CmkGhostWidth :variants="timeWidthVariants">
      <span :aria-label="emptyName(props.from.time)">{{ timeText(props.from.time) }}</span>
    </CmkGhostWidth>
    <span>{{ _t('To') }}</span>
    <span :aria-label="emptyName(props.to.date)">
      <b>{{ dateText(props.to.date) }}</b>
    </span>
    <span class="cmk-time-range-display__divider" aria-hidden="true">{{ untranslated('|') }}</span>
    <CmkGhostWidth :variants="timeWidthVariants">
      <span :aria-label="emptyName(props.to.time)">{{ timeText(props.to.time) }}</span>
    </CmkGhostWidth>
  </div>
</template>

<style scoped>
/* Columns: label | date | divider | time. */
.cmk-time-range-display {
  display: grid;
  grid-template-columns: repeat(4, max-content);
  align-items: center;
  gap: var(--dimension-2) var(--dimension-4);
  color: var(--font-color);
  font-variant-numeric: tabular-nums;
}

.cmk-time-range-display__divider {
  color: var(--font-color-dimmed);
}
</style>
