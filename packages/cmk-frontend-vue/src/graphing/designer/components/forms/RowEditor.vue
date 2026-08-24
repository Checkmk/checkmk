<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import { useItemValidation } from '../../composables/useItemValidation'
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

const { _t } = usei18n()

const { isValid } = useItemValidation(store.items)
const { issueMessage } = useValidationMessages()

type PreviewAlert = 'added' | 'updated'

const alert = ref<PreviewAlert | null>(null)

const formStore: GraphItemsStore = {
  ...store,
  replace: (updated: DesignerItem) => {
    const wasValid = isValid(row)
    store.replace(updated)
    alert.value = !isValid(updated) ? null : wasValid ? 'updated' : 'added'
  }
}

function previewAlertText(preview: PreviewAlert): TranslatedString {
  switch (preview) {
    case 'added':
      return _t('Preview added to graph')
    case 'updated':
      return _t('Preview updated')
  }
}

const alertText = computed<TranslatedString | null>(() =>
  alert.value === null ? null : previewAlertText(alert.value)
)

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
  <div
    class="graphing-row-editor"
    role="group"
    :aria-label="_t('Source %{id} details', { id: row.id })"
  >
    <FormulaForm
      v-if="row.type === 'rrd_formula'"
      :item="row"
      :store="store"
      :ast-errors="messagesFor('ast')"
    />
    <template v-else>
      <CmkAlertBox
        v-if="alertText !== null"
        class="graphing-row-editor__alert"
        variant="success"
        size="small"
        auto-dismiss
        @update:open="alert = null"
      >
        {{ alertText }}
      </CmkAlertBox>

      <RrdForm
        v-if="row.type === 'rrd_metric' || row.type === 'rrd_query'"
        :item="row"
        :store="formStore"
        :host-name-errors="messagesFor('host_name')"
        :service-name-errors="messagesFor('service_name')"
        :metric-name-errors="messagesFor('metric_name')"
        :host-filter-errors="messagesFor('host_filter')"
        :service-filter-errors="messagesFor('service_filter')"
      />
      <ConstantLineForm
        v-else-if="row.type === 'constant'"
        :item="row"
        :store="formStore"
        :value-errors="messagesFor('value')"
      />
      <ServiceReferenceLineForm
        v-else-if="row.type === 'scalar'"
        :item="row"
        :store="formStore"
        :thresholds="thresholds"
        :host-name-errors="messagesFor('host_name')"
        :service-name-errors="messagesFor('service_name')"
        :metric-name-errors="messagesFor('metric_name')"
      />
      <MetricBackendForm
        v-else-if="row.type === 'metric_backend'"
        :item="row"
        :store="formStore"
        :metric-name-errors="messagesFor('metric_name')"
        :consolidation-errors="messagesFor('consolidation_function')"
      />
    </template>
  </div>
</template>

<style scoped>
.graphing-row-editor {
  position: relative;
  padding: var(--dimension-5) var(--dimension-4) var(--dimension-7) 0;
}

.graphing-row-editor__alert {
  position: absolute;
  top: var(--dimension-5);
  right: var(--dimension-4);
  z-index: 1;
  white-space: nowrap;
  margin: 0;
  padding: var(--dimension-2) var(--dimension-4);
  align-items: center;
}
</style>
