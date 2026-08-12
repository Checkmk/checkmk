<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DesignerItem } from '../../drafts'
import ConstantLineForm from './ConstantLineForm.vue'
import FormulaForm from './FormulaForm.vue'
import MetricBackendForm from './MetricBackendForm.vue'
import RrdForm from './RrdForm.vue'
import ServiceReferenceLineForm from './ServiceReferenceLineForm.vue'

const { row, store, thresholds } = defineProps<{
  row: DesignerItem
  store: GraphItemsStore
  thresholds: { warning: string; critical: string }
}>()
</script>

<template>
  <div class="graphing-row-editor">
    <FormulaForm v-if="row.type === 'rrd_formula'" :item="row" :store="store" />
    <div v-else class="graphing-row-editor__panel">
      <RrdForm
        v-if="row.type === 'rrd_metric' || row.type === 'rrd_query'"
        :item="row"
        :store="store"
      />
      <ConstantLineForm v-else-if="row.type === 'constant'" :item="row" :store="store" />
      <ServiceReferenceLineForm
        v-else-if="row.type === 'scalar'"
        :item="row"
        :store="store"
        :thresholds="thresholds"
      />
      <MetricBackendForm v-else-if="row.type === 'metric_backend'" :item="row" :store="store" />
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
