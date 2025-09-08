<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkInput from '@/components/user-input/CmkInput.vue'

import type { Age } from './GraphTimeRange.vue'

const { _t } = usei18n()

const durationModel = defineModel<Age>({
  default: () => ({ days: 0, hours: 0, minutes: 0, seconds: 0 })
})
</script>

<template>
  <div class="custom-duration-fields">
    <CmkInput v-model="durationModel.days" type="number" :unit="_t('days')" field-size="SMALL" />
    <CmkInput v-model="durationModel.hours" type="number" :unit="_t('hours')" field-size="SMALL" />
    <CmkInput v-model="durationModel.minutes" type="number" :unit="_t('mins')" field-size="SMALL" />
    <CmkInput v-model="durationModel.seconds" type="number" :unit="_t('secs')" field-size="SMALL" />
  </div>
</template>

<style scoped>
.custom-duration-fields {
  display: flex;
  gap: var(--spacing);
  margin-top: var(--spacing);
  justify-content: left;
  align-items: center;
}
</style>
