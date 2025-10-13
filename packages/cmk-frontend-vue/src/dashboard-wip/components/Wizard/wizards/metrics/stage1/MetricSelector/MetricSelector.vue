<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import { MetricSelection } from '@/dashboard-wip/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'

import CombinedMetricSelector from './CombinedMetric.vue'
import SingleMetricSelector from './SingleMetric.vue'
import type { UseCombinedMetric } from './useCombinedMetric'
import type { UseSingleMetric } from './useSingleMetric'

const { _t } = usei18n()

const metricType = defineModel<MetricSelection>('metricType', {
  default: MetricSelection.SINGLE_METRIC
})
const singleMetricHandler = defineModel<UseSingleMetric>('singleMetricHandler', { required: true })
const combinedMetricHandler = defineModel<UseCombinedMetric>('combinedMetricHandler', {
  required: true
})

const _updateMetricType = (value: string) => {
  metricType.value =
    value === 'SINGLE' ? MetricSelection.SINGLE_METRIC : MetricSelection.COMBINED_GRAPH
}
</script>

<template>
  <ToggleButtonGroup
    :model-value="metricType"
    :options="[
      { label: _t('Metric (single)'), value: MetricSelection.SINGLE_METRIC },
      { label: _t('Graph (combined)'), value: MetricSelection.COMBINED_GRAPH }
    ]"
    @update:model-value="_updateMetricType"
  />
  <CmkIndent>
    <div class="db-metric-selector__container">
      <div v-if="metricType === MetricSelection.SINGLE_METRIC">
        <CmkLabel>{{ _t('Service metric') }} (*)</CmkLabel>
        <ContentSpacer />
        <CmkIndent>
          <SingleMetricSelector v-model:handler="singleMetricHandler" />
        </CmkIndent>
      </div>
      <div v-if="metricType === MetricSelection.COMBINED_GRAPH">
        <CmkLabel>{{ _t('Service graph') }} (*)</CmkLabel>
        <ContentSpacer />
        <CombinedMetricSelector v-model:handler="combinedMetricHandler" />
      </div>
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-metric-selector__container {
  background-color: var(--ux-theme-3);
  padding: 10px;
}
</style>
