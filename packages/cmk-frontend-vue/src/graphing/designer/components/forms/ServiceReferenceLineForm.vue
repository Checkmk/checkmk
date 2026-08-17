<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import { type DraftScalarItem, scalarColor } from '../../drafts'
import type { ScalarItem } from '../../types'
import HostNameSelect from './fields/HostNameSelect.vue'
import ServiceMetricSelect from './fields/ServiceMetricSelect.vue'
import ServiceNameSelect from './fields/ServiceNameSelect.vue'
import { hostServiceContext } from './fields/utils'

const { item, store, thresholds, hostNameErrors, serviceNameErrors, metricNameErrors } =
  defineProps<{
    item: DraftScalarItem
    store: GraphItemsStore
    thresholds: { warning: string; critical: string }
    hostNameErrors: TranslatedString[]
    serviceNameErrors: TranslatedString[]
    metricNameErrors: TranslatedString[]
  }>()

const { _t } = usei18n()

const thresholdId = useId()

const SCALAR_TYPE_TITLES: Record<ScalarItem['scalar_type'], TranslatedString> = {
  warning: _t('Warning'),
  critical: _t('Critical'),
  warning_lower: _t('Warning (lower)'),
  critical_lower: _t('Critical (lower)'),
  min: _t('Minimum'),
  max: _t('Maximum')
}
const SCALAR_TYPES = Object.keys(SCALAR_TYPE_TITLES) as ScalarItem['scalar_type'][]

const scalarTypeSuggestions = {
  type: 'fixed' as const,
  suggestions: SCALAR_TYPES.map((name) => ({ name, title: SCALAR_TYPE_TITLES[name] }))
}

const metricContext = computed(() => hostServiceContext(item.host_name, item.service_name))

/** A palette color to fall back to; never keeps a threshold color on the way out. */
function paletteFallback(color: string): string {
  return color === thresholds.warning || color === thresholds.critical
    ? store.nextColor.value
    : color
}

function onScalarTypeChange(value: string | null): void {
  const scalarType = SCALAR_TYPES.find((candidate) => candidate === value)
  if (scalarType !== undefined) {
    store.replace({
      ...item,
      scalar_type: scalarType,
      color: scalarColor(scalarType, paletteFallback(item.color), thresholds)
    })
  }
}

/** Selecting upstream clears the dependent selections (host -> service -> metric). */
function onHostChange(hostName: string | null): void {
  store.replace({ ...item, host_name: hostName, service_name: null, metric_name: null })
}

function onServiceChange(serviceName: string | null): void {
  store.replace({ ...item, service_name: serviceName, metric_name: null })
}

function onMetricChange(metricName: string | null): void {
  store.replace({ ...item, metric_name: metricName })
}
</script>

<template>
  <div class="graphing-service-reference-line-form">
    <HostNameSelect
      :model-value="item.host_name"
      required
      :errors="hostNameErrors"
      @update:model-value="onHostChange"
    />
    <ServiceNameSelect
      :model-value="item.service_name"
      :host-name="item.host_name"
      required
      :errors="serviceNameErrors"
      @update:model-value="onServiceChange"
    />
    <ServiceMetricSelect
      :model-value="item.metric_name"
      :context="metricContext"
      required
      :errors="metricNameErrors"
      @update:model-value="onMetricChange"
    />

    <div class="graphing-service-reference-line-form__field">
      <CmkLabel variant="subtitle" :for="thresholdId">{{ _t('Threshold') }}</CmkLabel>
      <CmkDropdown
        :model-value="item.scalar_type"
        :component-id="thresholdId"
        :options="scalarTypeSuggestions"
        :label="_t('Threshold type')"
        floating
        @update:model-value="onScalarTypeChange"
      />
    </div>
  </div>
</template>

<style scoped>
.graphing-service-reference-line-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.graphing-service-reference-line-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
