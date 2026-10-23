<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { Age } from './GraphTimeRange.vue'

const { _t } = usei18n()

const durationModel = defineModel<Age>({
  default: () => ({ days: 0, hours: 0, minutes: 0, seconds: 0 })
})
</script>

<template>
  <div class="db-duration-fields--container">
    <CmkInput v-model="durationModel.days" type="number" :unit="_t('Days')" field-size="small" />
    <CmkInput v-model="durationModel.hours" type="number" :unit="_t('Hours')" field-size="small" />
    <CmkInput
      v-model="durationModel.minutes"
      type="number"
      :unit="_t('Minutes')"
      field-size="small"
    />
    <CmkInput
      v-model="durationModel.seconds"
      type="number"
      :unit="_t('Seconds')"
      field-size="small"
    />
  </div>
</template>

<style scoped>
.db-duration-fields--container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  margin-top: var(--spacing);
  align-items: flex-start;
}
</style>
