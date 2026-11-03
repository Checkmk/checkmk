<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { LabelValue } from '@/monitoring/shared/api/types'
import FilterTag from '@/monitoring/shared/components/FilterTag.vue'
import {
  type LabelCellItem,
  labelItemText
} from '@/monitoring/shared/components/cell/labelCellItem'
import { toLabelItems } from '@/monitoring/shared/labels'
import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'

const DEFAULT_LIMIT = 5

const props = withDefaults(
  defineProps<{
    labels: Record<string, LabelValue>
    limit?: number
    /** The filter a click on a label narrows the listing to; without it the labels are plain. */
    filterBy?: ((item: LabelCellItem) => ColumnCondition) | undefined
  }>(),
  { limit: DEFAULT_LIMIT }
)

const { _t } = usei18n()

const expanded = ref(false)

const items = computed(() => toLabelItems(props.labels))

const hasOverflow = computed(() => items.value.length > props.limit)
const visibleItems = computed(() =>
  expanded.value ? items.value : items.value.slice(0, props.limit)
)
</script>

<template>
  <div class="monitoring-overview-labels">
    <FilterTag
      v-for="item in visibleItems"
      :key="labelItemText(item)"
      :item="item"
      size="small"
      spacing="none"
      :filter-by="filterBy"
    />
    <CmkButton v-if="hasOverflow" size="small" variant="text" @click="expanded = !expanded">
      {{ expanded ? _t('show less') : `+${items.length - limit}` }}
    </CmkButton>
  </div>
</template>

<style scoped>
.monitoring-overview-labels {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
  align-items: center;
}
</style>
