<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkInput from '@/components/user-input/CmkInput.vue'

const { _t } = usei18n()

const dateRangeModel = defineModel<{
  from: {
    year: number
    month: number
    day: number
  }
  to: {
    year: number
    month: number
    day: number
  }
}>({
  default: () => ({
    from: {
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
      day: new Date().getDate()
    },
    to: {
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
      day: new Date().getDate()
    }
  })
})
</script>

<template>
  <div class="custom-date-range">
    <div class="from_date">
      <div class="date_title">{{ _t('From:') }}</div>
      <div class="date_fields">
        <div class="field">
          <span class="unit">{{ _t('Year') }}</span>
          <CmkInput v-model="dateRangeModel.from.year" type="number" field-size="SMALL" />
        </div>
        <div class="field">
          <span class="unit">{{ _t('Month') }}</span>
          <CmkInput v-model="dateRangeModel.from.month" type="number" field-size="SMALL" />
        </div>
        <div class="field">
          <span class="unit">{{ _t('Day') }}</span>
          <CmkInput v-model="dateRangeModel.from.day" type="number" field-size="SMALL" />
        </div>
      </div>
    </div>
    <div class="to_date">
      <div class="date_title">{{ _t('To:') }}</div>
      <div class="date_fields">
        <div class="field">
          <span class="unit">{{ _t('Year') }}</span>
          <CmkInput v-model="dateRangeModel.to.year" type="number" field-size="SMALL" />
        </div>
        <div class="field">
          <span class="unit">{{ _t('Month') }}</span>
          <CmkInput v-model="dateRangeModel.to.month" type="number" field-size="SMALL" />
        </div>
        <div class="field">
          <span class="unit">{{ _t('Day') }}</span>
          <CmkInput v-model="dateRangeModel.to.day" type="number" field-size="SMALL" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-date-range {
  margin-top: var(--spacing);
  min-height: 40px;
  font-size: var(--font-size-small);
}

.custom-date-range .from_date,
.custom-date-range .to_date {
  float: left;
  display: flex;
  justify-content: center;
  align-items: center;
}

.custom-date-range .date_title {
  display: inline;
  margin-right: var(--spacing);
}

.custom-date-range .field {
  position: relative;
  height: 40px;
  width: 60px;
  float: inline-start;
}
</style>
