<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import FormMetricBackendCustomQuery from '@/metric-backend-custom-query/FormMetricBackendCustomQuery.vue'

const { _t } = usei18n()

const metricName = defineModel<string | null>('metricName', { required: true })
const metricTypes = defineModel<string[]>('metricTypes', { required: true })
const attributeFilter = defineModel<AttributeFilter | undefined>('attributeFilter', {
  required: true
})
const consolidation = defineModel<WireConsolidationFunction>('consolidation', { required: true })
</script>

<template>
  <div class="mode-custom-services-define-metric-step">
    <CmkParagraph class="mode-custom-services-define-metric-step__lead">{{
      _t('Select the metric for this service')
    }}</CmkParagraph>
    <FormMetricBackendCustomQuery
      v-model:metric-name="metricName"
      v-model:metric-types="metricTypes"
      v-model:attribute-filter="attributeFilter"
      v-model:consolidation="consolidation"
    />
  </div>
</template>

<style scoped>
.mode-custom-services-define-metric-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  max-width: 620px;
}
</style>
