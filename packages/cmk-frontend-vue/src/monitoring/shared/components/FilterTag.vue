<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTag, { type Sizes, type Spacings } from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'

import { AFTER_NARROW, MONITORING_SERVICE } from './MonitoringTableContext'
import {
  type LabelCellItem,
  labelItemContent,
  labelItemText,
  labelItemValue
} from './cell/labelCellItem'

const props = defineProps<{
  item: LabelCellItem
  size?: Sizes | undefined
  spacing?: Spacings | undefined
  /** What a click narrows the listing to; without it the tag is plain. */
  filterBy?: ((item: LabelCellItem) => ColumnCondition) | undefined
}>()

const { _t } = usei18n()

// A dashboard widget has no listing of its own to narrow, so it provides no service.
const service = inject(MONITORING_SERVICE, null)
const afterNarrow = inject(AFTER_NARROW, null)

const interactive = computed(() => service !== null && props.filterBy !== undefined)

function narrow(): void {
  if (service && props.filterBy) {
    service.showOnly(props.filterBy(props.item))
    afterNarrow?.()
  }
}
</script>

<template>
  <CmkTag
    :size="size"
    :spacing="spacing"
    :variant="item.variant ?? 'fill'"
    :color="item.color ?? 'default'"
    :content="labelItemContent(item)"
    :value="labelItemValue(item)"
    :interactive="interactive"
    :title="
      interactive ? _t('Filter by %{entry}', { entry: labelItemText(item) }) : labelItemText(item)
    "
    @click="narrow"
  />
</template>
