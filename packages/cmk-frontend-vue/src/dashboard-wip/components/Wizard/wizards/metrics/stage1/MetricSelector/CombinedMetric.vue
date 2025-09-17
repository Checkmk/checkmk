<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import AutocompleteCombinedMetrics from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteCombinedMetrics.vue'

import type { UseCombinedMetric } from './useCombinedMetric'

const { _t } = usei18n()

const handler = defineModel<UseCombinedMetric>('handler', { required: true })
</script>

<template>
  <div class="db-combined-metric__container">
    <CmkLabel>{{ _t('Service metric') }} (*)</CmkLabel>
    <AutocompleteCombinedMetrics v-model:combined-metrics="handler.combinedMetric.value" />
    <CmkInlineValidation
      v-if="handler.combinedMetricValidationError.value"
      :validation="[_t('Must select an option')]"
    />
  </div>
</template>

<style scoped>
.db-combined-metric__container {
  display: flex;
  flex-direction: column;
}
</style>
