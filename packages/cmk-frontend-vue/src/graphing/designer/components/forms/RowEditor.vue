<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import { useValidationMessages } from '../../composables/useValidationMessages'
import type { DesignerItem } from '../../drafts'
import type { RowField, RowIssue } from '../../validation'
import ConstantLineForm from './ConstantLineForm.vue'
import FormulaForm from './FormulaForm.vue'
import MetricBackendForm from './MetricBackendForm.vue'
import RrdForm from './RrdForm.vue'
import ServiceReferenceLineForm from './ServiceReferenceLineForm.vue'

const { row, store, thresholds, issues } = defineProps<{
  row: DesignerItem
  store: GraphItemsStore
  thresholds: { warning: string; critical: string }
  issues: readonly RowIssue[]
}>()

const { issueMessage } = useValidationMessages()

const messagesByField = computed(() => {
  const byField = new Map<RowField, TranslatedString[]>()
  for (const issue of issues) {
    byField.set(issue.field, [...(byField.get(issue.field) ?? []), issueMessage(issue)])
  }
  return byField
})

function messagesFor(field: RowField): TranslatedString[] {
  return messagesByField.value.get(field) ?? []
}
</script>

<template>
  <div class="graphing-row-editor">
    <FormulaForm
      v-if="row.type === 'rrd_formula'"
      :item="row"
      :store="store"
      :ast-errors="messagesFor('ast')"
    />
    <div v-else class="graphing-row-editor__panel">
      <RrdForm
        v-if="row.type === 'rrd_metric' || row.type === 'rrd_query'"
        :item="row"
        :store="store"
        :host-name-errors="messagesFor('host_name')"
        :service-name-errors="messagesFor('service_name')"
        :metric-name-errors="messagesFor('metric_name')"
      />
      <ConstantLineForm
        v-else-if="row.type === 'constant'"
        :item="row"
        :store="store"
        :value-errors="messagesFor('value')"
      />
      <ServiceReferenceLineForm
        v-else-if="row.type === 'scalar'"
        :item="row"
        :store="store"
        :thresholds="thresholds"
        :host-name-errors="messagesFor('host_name')"
        :service-name-errors="messagesFor('service_name')"
        :metric-name-errors="messagesFor('metric_name')"
      />
      <MetricBackendForm
        v-else-if="row.type === 'metric_backend'"
        :item="row"
        :store="store"
        :metric-name-errors="messagesFor('metric_name')"
        :consolidation-errors="messagesFor('consolidation_function')"
      />
    </div>
  </div>
</template>

<style scoped>
.graphing-row-editor {
  --graphing-row-editor-panel-border: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .graphing-row-editor {
  --graphing-row-editor-panel-border: var(--color-mid-grey-90);
}

.graphing-row-editor__panel {
  overflow: hidden;
  border: 1px solid var(--graphing-row-editor-panel-border);
  border-radius: var(--border-radius);
}
</style>
