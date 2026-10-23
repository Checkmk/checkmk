<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import AutocompleteMonitoredMetrics from '@/dashboard/components/Wizard/components/autocompleters/AutocompleteMonitoredMetrics.vue'
import type { ElementSelection } from '@/dashboard/components/Wizard/types'
import { MetricSelection } from '@/dashboard/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'

import GraphAutocompleter from './GraphAutocompleter.vue'
import type { UseMetric } from './useMetric'

const { _t } = usei18n()

interface MetricSelectorProps {
  hostSelectionMode: ElementSelection
  serviceSelectionMode: ElementSelection
  context: ConfiguredFilters
  availableMetricTypes?: MetricSelection[]
}

const props = withDefaults(defineProps<MetricSelectorProps>(), {
  availableMetricTypes: () => [MetricSelection.SINGLE_METRIC, MetricSelection.COMBINED_GRAPH]
})

const metricType = defineModel<MetricSelection>('metricType', {
  default: undefined
})
const handler = defineModel<UseMetric>('metricHandler', { required: true })

const isSingleMetricDisabled = computed(
  () => !props.availableMetricTypes.includes(MetricSelection.SINGLE_METRIC)
)
const isCombinedGraphDisabled = computed(
  () => !props.availableMetricTypes.includes(MetricSelection.COMBINED_GRAPH)
)

const _updateMetricType = (value: string) => {
  metricType.value =
    value === 'SINGLE' ? MetricSelection.SINGLE_METRIC : MetricSelection.COMBINED_GRAPH
}
</script>

<template>
  <CmkToggleButtonGroup
    :model-value="metricType"
    :options="[
      {
        label: _t('Metric (single)'),
        value: MetricSelection.SINGLE_METRIC,
        disabled: isSingleMetricDisabled,
        disabledTooltip: isSingleMetricDisabled
          ? _t('Available in Checkmk Pro or higher.')
          : undefined
      },
      {
        label: _t('Graph (combined)'),
        value: MetricSelection.COMBINED_GRAPH,
        disabled: isCombinedGraphDisabled
      }
    ]"
    @update:model-value="_updateMetricType"
  />

  <CmkIndent>
    <div class="db-metric-selector__base-container">
      <span class="db-metric-selector__title">{{
        metricType === MetricSelection.SINGLE_METRIC ? _t('Service metric') : _t('Service graph')
      }}</span>
      <CmkLabelRequired space="before" />

      <ContentSpacer :dimension="4" />

      <CmkIndent class="db-metric-selector__indent">
        <div class="db-metric-selector__metric-selector">
          <AutocompleteMonitoredMetrics
            v-if="metricType === MetricSelection.SINGLE_METRIC"
            v-model:service-metrics="handler.metric.value"
            :context="context"
            width="fill"
          />
          <GraphAutocompleter
            v-else
            v-model:combined-metrics="handler.metric.value"
            :host-selection-mode="hostSelectionMode"
            :service-selection-mode="serviceSelectionMode"
            :context="context"
            width="fill"
          />
        </div>
        <div v-if="handler.metricValidationError.value">
          <CmkInlineValidation :validation="[_t('Must select an option')]" />
        </div>
      </CmkIndent>
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-metric-selector__base-container {
  background-color: var(--ux-theme-2);
  padding: var(--dimension-7);
}

.db-metric-selector__title {
  color: var(--font-color);
  font-size: 12px;
  font-weight: bold;
}

.db-metric-selector__indent {
  margin-left: 0 !important;
  padding-left: var(--dimension-4);
  padding-top: 0;
  padding-bottom: 0;
}
</style>
