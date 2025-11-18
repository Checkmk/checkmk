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
  <div class="db-date-range-fields">
    <div class="db-date-range-fields--from-date">
      <div class="db-date-range-fields--title">{{ _t('From:') }}</div>
      <div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Year') }}</span>
          <CmkInput v-model="dateRangeModel.from.year" type="number" field-size="SMALL" />
        </div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Month') }}</span>
          <CmkInput v-model="dateRangeModel.from.month" type="number" field-size="SMALL" />
        </div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Day') }}</span>
          <CmkInput v-model="dateRangeModel.from.day" type="number" field-size="SMALL" />
        </div>
      </div>
    </div>
    <div class="db-date-range-fields--to-date">
      <div class="db-date-range-fields--title">{{ _t('To:') }}</div>
      <div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Year') }}</span>
          <CmkInput v-model="dateRangeModel.to.year" type="number" field-size="SMALL" />
        </div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Month') }}</span>
          <CmkInput v-model="dateRangeModel.to.month" type="number" field-size="SMALL" />
        </div>
        <div class="db-date-range-fields--field">
          <span>{{ _t('Day') }}</span>
          <CmkInput v-model="dateRangeModel.to.day" type="number" field-size="SMALL" />
        </div>
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

.db-date-range-fields .db-date-range-fields--from-date,
.db-date-range-fields .db-date-range-fields--to-date {
  float: left;
  display: flex;
  justify-content: center;
  align-items: center;
}

.db-date-range-fields .db-date-range-fields--title {
  display: inline;
  margin-right: var(--spacing);
}

.db-date-range-fields .db-date-range-fields--field {
  position: relative;
  height: 40px;
  width: 60px;
  float: inline-start;
}
</style>
