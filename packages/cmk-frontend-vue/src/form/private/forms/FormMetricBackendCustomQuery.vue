<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'

import useId from '@/lib/useId'

import { type ValidationMessages, useValidation } from '@/form/private/validation'

import FormMetricBackendCustomQuery from '@/graph-designer/FormMetricBackendCustomQuery.vue'

const props = defineProps<{
  spec: MetricBackendCustomQuery
  backendValidation: ValidationMessages
}>()

const data = defineModel<MetricBackendCustomQuery>('data', { required: true })
const [_validation, value] = useValidation<MetricBackendCustomQuery>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <FormMetricBackendCustomQuery
    :id="componentId"
    v-model:metric-name="value.metric_name"
    v-model:resource-attributes="value.resource_attributes"
    v-model:scope-attributes="value.scope_attributes"
    v-model:data-point-attributes="value.data_point_attributes"
    v-model:aggregation-sum="value.aggregation_sum"
    v-model:aggregation-histogram-percentile="value.aggregation_histogram_percentile"
  />
</template>
