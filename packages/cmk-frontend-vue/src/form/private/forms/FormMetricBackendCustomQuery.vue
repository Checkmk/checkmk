<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormHelp from '@/form/private/FormHelp.vue'
import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendCustomQuery from '@/graph-designer/FormMetricBackendCustomQuery.vue'

const { _t } = usei18n()

const props = defineProps<{
  spec: MetricBackendCustomQuery
  backendValidation: ValidationMessages
}>()

const data = defineModel<MetricBackendCustomQuery>('data', { required: true })

const componentId = useId()

const serviceNameTemplateHelp = _t(
  'Available macros: <tt>$SERIES_ID$</tt>, <tt>$METRIC_NAME$</tt>, <tt>$RESOURCE_ATTR.&lt;key&gt;$</tt>, <tt>$SCOPE_ATTR.&lt;key&gt;$</tt>, <tt>$DATA_POINT_ATTR.&lt;key&gt;$</tt>'
)
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
  >
    <template #additional-rows>
      <tr>
        <td>{{ _t('Service name template') }}</td>
        <td>
          <div class="form-metric-backend-custom-query__service-name-template">
            <CmkInput
              v-model="data.service_name_template"
              type="text"
              field-size="LARGE"
              :placeholder="_t('Service name template')"
            />
            <CmkHelpText :help="serviceNameTemplateHelp" />
          </div>
          <FormHelp :help="serviceNameTemplateHelp" />
        </td>
      </tr>
    </template>
  </FormMetricBackendCustomQuery>
</template>

<style scoped>
.form-metric-backend-custom-query__service-name-template {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
