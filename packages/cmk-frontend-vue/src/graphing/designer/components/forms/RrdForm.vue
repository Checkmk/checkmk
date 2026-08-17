<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabeledSwitch from 'cmk-ui-library/components/CmkLabeledSwitch.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import {
  type DraftRRDMetricItem,
  type DraftRRDQueryItem,
  rrdMetricToQueryDraft,
  rrdQueryToMetricDraft
} from '../../drafts'
import RrdMetricForm from './RrdMetricForm.vue'
import RrdQueryForm from './RrdQueryForm.vue'
import SourceFormStack from './SourceFormStack.vue'
import SourceFormText from './SourceFormText.vue'

const { item, store, hostNameErrors, serviceNameErrors, metricNameErrors } = defineProps<{
  item: DraftRRDMetricItem | DraftRRDQueryItem
  store: GraphItemsStore
  hostNameErrors: TranslatedString[]
  serviceNameErrors: TranslatedString[]
  metricNameErrors: TranslatedString[]
}>()

const { _t } = usei18n()

function onModeChange(isQuery: boolean): void {
  if (isQuery && item.type === 'rrd_metric') {
    store.replace(rrdMetricToQueryDraft(item))
  } else if (!isQuery && item.type === 'rrd_query') {
    store.replace(rrdQueryToMetricDraft(item, store.nextColor.value))
  }
}
</script>

<template>
  <SourceFormStack spacing="section">
    <CmkLabeledSwitch
      :model-value="item.type === 'rrd_query'"
      :off-label="_t('Single selection')"
      :on-label="_t('Multiple selections')"
      @update:model-value="onModeChange"
    />

    <SourceFormStack spacing="label">
      <SourceFormText variant="description">{{ _t('Show') }}</SourceFormText>

      <RrdMetricForm
        v-if="item.type === 'rrd_metric'"
        :item="item"
        :store="store"
        :host-name-errors="hostNameErrors"
        :service-name-errors="serviceNameErrors"
        :metric-name-errors="metricNameErrors"
      />
      <RrdQueryForm
        v-else-if="item.type === 'rrd_query'"
        :item="item"
        :store="store"
        :metric-name-errors="metricNameErrors"
      />
    </SourceFormStack>
  </SourceFormStack>
</template>
