<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import AutocompleteHost from '@/dashboard/components/Wizard/components/autocompleters/AutocompleteHost.vue'
import AutocompleteMonitoredMetrics from '@/dashboard/components/Wizard/components/autocompleters/AutocompleteMonitoredMetrics.vue'
import AutocompleteService from '@/dashboard/components/Wizard/components/autocompleters/AutocompleteService.vue'
import type { ElementSelection } from '@/dashboard/components/Wizard/types'
import { MetricSelection } from '@/dashboard/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'

import GraphAutocompleter from './GraphAutocompleter.vue'
import type { UseMetric } from './useMetric'

const { _t } = usei18n()

interface MetricSelectorProps {
  hostSelectionMode: ElementSelection
  serviceSelectionMode: ElementSelection
  availableMetricTypes?: MetricSelection[]
}

const props = withDefaults(defineProps<MetricSelectorProps>(), {
  availableMetricTypes: () => [MetricSelection.SINGLE_METRIC, MetricSelection.COMBINED_GRAPH]
})

const metricType = defineModel<MetricSelection>('metricType', {
  default: undefined
})
const handler = defineModel<UseMetric>('metricHandler', { required: true })

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
        disabled: !props.availableMetricTypes.includes(MetricSelection.SINGLE_METRIC)
      },
      {
        label: _t('Graph (combined)'),
        value: MetricSelection.COMBINED_GRAPH,
        disabled: !props.availableMetricTypes.includes(MetricSelection.COMBINED_GRAPH)
      }
    ]"
    @update:model-value="_updateMetricType"
  />
  <CmkIndent>
    <div
      v-if="metricType === MetricSelection.SINGLE_METRIC"
      class="db-metric-selector__base-container"
    >
      <CmkLabel>{{ _t('Service metric') }}</CmkLabel
      ><CmkLabelRequired space="before" />

      <ContentSpacer :dimension="4" />

      <CmkIndent>
        <CmkLabel>{{ _t('Filter service metric by') }}</CmkLabel>
        <CmkHelpText
          :help="
            _t(
              'Use these fields to narrow down the list of available service metrics.<br />Click the Host name or Service label to clear the filter.'
            )
          "
        />
        <ContentSpacer :dimension="2" />
        <div class="db-metric-selector__container">
          <div class="db-metric-selector__host-filter">
            <div class="db-metric-selector__cell">
              <div class="db-metric-selector__label" @click="() => (handler.host.value = null)">
                <CmkLabel style="cursor: pointer">{{ _t('Host name') }}:</CmkLabel>
              </div>

              <div class="db-metric-selector__autocompleter">
                <AutocompleteHost
                  v-model:host-name="handler.host.value"
                  width="fill"
                  :placeholder="_t('Select')"
                />
              </div>
            </div>
          </div>

          <div class="db-metric-selector__service-filter">
            <div class="db-metric-selector__cell">
              <div class="db-metric-selector__label" @click="() => (handler.service.value = null)">
                <CmkLabel style="cursor: pointer">{{ _t('Service') }}:</CmkLabel>
              </div>

              <div class="db-metric-selector__autocompleter">
                <AutocompleteService
                  v-model:service-description="handler.service.value"
                  :host-name="handler.host.value"
                  width="fill"
                  :placeholder="_t('Select')"
                />
              </div>
            </div>
          </div>

          <div class="db-metric-selector__metric-selector">
            <AutocompleteMonitoredMetrics
              v-if="metricType === MetricSelection.SINGLE_METRIC"
              v-model:service-metrics="handler.metric.value"
              :host-name="handler.host.value"
              :service-description="handler.service.value"
              width="fill"
            />
          </div>
          <div v-if="handler.metricValidationError.value">
            <CmkInlineValidation :validation="[_t('Must select an option')]" />
          </div>
        </div>
      </CmkIndent>
    </div>

    <div v-else class="db-metric-selector__base-container">
      <CmkLabel>{{ _t('Service graph') }}</CmkLabel
      ><CmkLabelRequired space="before" />

      <ContentSpacer :dimension="4" />

      <CmkIndent>
        <div class="db-metric-selector__container"></div>
        <div class="db-metric-selector__metric-selector">
          <GraphAutocompleter
            v-model:combined-metrics="handler.metric.value"
            :host-selection-mode="hostSelectionMode"
            :service-selection-mode="serviceSelectionMode"
            width="fill"
          />
          <div v-if="handler.metricValidationError.value">
            <CmkInlineValidation :validation="[_t('Must select an option')]" />
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
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0 var(--dimension-4);
}

.db-metric-selector__host-filter {
  grid-area: 1 / 1 / 2 / 2;
  padding-bottom: var(--dimension-4);
}

.db-metric-selector__service-filter {
  grid-area: 1 / 2 / 2 / 3;
  padding-bottom: var(--dimension-4);
}

.db-metric-selector__metric-selector {
  grid-area: 2 / 1 / 3 / 3;
  padding-bottom: var(--dimension-4);
}

.db-metric-selector__cell {
  display: flex;
  flex-flow: row nowrap;
  justify-content: space-between;
  align-items: center;
}

.db-metric-selector__label {
  white-space: nowrap;
}

.db-metric-selector__autocompleter {
  flex: 1;
  min-width: 0;
}
</style>
