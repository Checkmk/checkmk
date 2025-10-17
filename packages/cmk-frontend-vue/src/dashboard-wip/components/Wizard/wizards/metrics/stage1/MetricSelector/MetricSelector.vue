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
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import AutocompleteAvailableGraphTemplates from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteAvailableGraphTemplates.vue'
import AutocompleteHost from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteHost.vue'
import AutocompleteMonitoredMetrics from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteMonitoredMetrics.vue'
import AutocompleteService from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteService.vue'
import { MetricSelection } from '@/dashboard-wip/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'

import type { UseMetric } from './useMetric'

const { _t } = usei18n()

const metricType = defineModel<MetricSelection>('metricType', {
  default: MetricSelection.SINGLE_METRIC
})
const handler = defineModel<UseMetric>('metricHandler', { required: true })

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
    <div class="db-metric-selector__base-container">
      <CmkLabel v-if="metricType === MetricSelection.SINGLE_METRIC"
        >{{ _t('Service metric') }} (*)</CmkLabel
      >
      <CmkLabel v-else>{{ _t('Service graph') }} (*)</CmkLabel>
      <ContentSpacer />
      <CmkIndent>
        <div class="db-metric-selector__container">
          <div class="row db-metric-selector__top-row">
            <div class="db-metric-selector__top-cell">
              <AutocompleteHost v-model:host-name="handler.host.value" />
            </div>
            <div class="db-metric-selector__top-cell">
              <AutocompleteService v-model:service-description="handler.service.value" />
            </div>
          </div>
          <div class="row db-metric-selector__bottom-row">
            <AutocompleteMonitoredMetrics
              v-if="metricType === MetricSelection.SINGLE_METRIC"
              v-model:service-metrics="handler.metric.value"
              :host-name="handler.host.value"
              :service-description="handler.service.value"
            />
            <AutocompleteAvailableGraphTemplates
              v-else
              v-model:combined-metrics="handler.metric.value"
              :host-name="handler.host.value"
              :service-description="handler.service.value"
            />
            <CmkInlineValidation
              v-if="handler.metricValidationError.value"
              :validation="[_t('Must select an option')]"
            />
          </div>
        </div>
      </CmkIndent>
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-metric-selector__base-container {
  background-color: var(--ux-theme-3);
  padding: 10px;
}

.db-metric-selector__container {
  display: flex;
  flex-direction: column;
}

.db-metric-selector__top-row {
  display: flex;
  flex: 1;
}

.db-metric-selector__top-cell {
  flex: 1;
  display: flex;
  justify-content: flex-start;
  align-items: flex-start;
  padding-bottom: 10px;
}

.db-metric-selector__bottom-row {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
}
</style>
