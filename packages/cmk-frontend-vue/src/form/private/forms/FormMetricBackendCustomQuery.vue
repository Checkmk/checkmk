<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'

import useId from '@/lib/useId'

import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendCustomQuery from '@/graph-designer/FormMetricBackendCustomQuery.vue'

const props = defineProps<{
  spec: MetricBackendCustomQuery
  backendValidation: ValidationMessages
}>()

const data = defineModel<MetricBackendCustomQuery>('data', { required: true })

const componentId = useId()
</script>

<template>
  <FormMetricBackendCustomQuery
    :id="componentId"
    v-model:metric-name="data.metric_name"
    v-model:resource-attributes="data.resource_attributes"
    v-model:scope-attributes="data.scope_attributes"
    v-model:data-point-attributes="data.data_point_attributes"
    v-model:aggregation-lookback="data.aggregation_lookback"
    v-model:aggregation-histogram-percentile="data.aggregation_histogram_percentile"
    :backend-validation="props.backendValidation"
  />
</template>
