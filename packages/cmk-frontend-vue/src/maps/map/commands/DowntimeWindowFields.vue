<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
When a downtime starts and ends, picked the way Checkmk's own "Schedule
downtime" action picks them: one date and time each, on a 24-hour clock.
-->
<script setup lang="ts">
import type { ZonedDateTime } from '@internationalized/date'
import CmkDateTimePicker from 'cmk-ui-library/components/date-time/CmkDateTimePicker.vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types'
import usei18n from 'cmk-ui-library/lib/i18n'

const range = defineModel<DateTimeRange>({ required: true })

const { _t } = usei18n()

const SETTINGS = { hourCycle: 24 } as const

function setFrom(from: ZonedDateTime): void {
  range.value = { ...range.value, from }
}

function setTo(to: ZonedDateTime): void {
  range.value = { ...range.value, to }
}
</script>

<template>
  <div class="maps-downtime-window-fields">
    <span class="maps-downtime-window-fields__label">{{ _t('From') }}</span>
    <CmkDateTimePicker
      :model-value="range.from"
      :settings="SETTINGS"
      :label="_t('Choose when the downtime starts')"
      @update:model-value="setFrom"
    />
    <span class="maps-downtime-window-fields__label">{{ _t('To') }}</span>
    <CmkDateTimePicker
      :model-value="range.to"
      :settings="SETTINGS"
      :label="_t('Choose when the downtime ends')"
      @update:model-value="setTo"
    />
  </div>
</template>

<style scoped>
.maps-downtime-window-fields {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  gap: var(--dimension-3) var(--dimension-4);
  font-size: var(--font-size-normal);
}

.maps-downtime-window-fields__label {
  color: var(--font-color);
}
</style>
