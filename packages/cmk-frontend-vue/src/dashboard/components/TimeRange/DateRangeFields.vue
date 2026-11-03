<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type CalendarDate, getLocalTimeZone, today } from '@internationalized/date'
import CmkDatePicker from 'cmk-ui-library/components/date-time/CmkDatePicker.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { DateRange } from './types'

const { _t } = usei18n()

const dateRange = defineModel<DateRange>({
  default: () => ({ from: today(getLocalTimeZone()), to: today(getLocalTimeZone()) })
})

function updateDate(key: keyof DateRange, value: CalendarDate): void {
  dateRange.value = { ...dateRange.value, [key]: value }
}
</script>

<template>
  <div class="db-date-range-fields">
    <div class="db-date-range-fields__container">
      <div class="db-date-range-fields__container-title">{{ _t('From:') }}</div>
      <div>
        <CmkDatePicker
          :model-value="dateRange.from"
          @update:model-value="updateDate('from', $event)"
        />
      </div>
      <div class="db-date-range-fields__container-title">{{ _t('To:') }}</div>
      <div>
        <CmkDatePicker :model-value="dateRange.to" @update:model-value="updateDate('to', $event)" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-date-range-fields {
  margin-top: var(--spacing);
  min-height: 40px;
  font-size: var(--font-size-small);
}

.db-date-range-fields__container {
  display: grid;
  grid-template-columns: max-content 1fr;
  grid-template-rows: auto auto;
  align-items: center;
  gap: var(--dimension-3);
}

.db-date-range-fields__container-title {
  justify-self: end;
}
</style>
