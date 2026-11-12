<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { LabelValue } from '@/monitoring/shared/api/types'
import type { LabelCellItem } from '@/monitoring/shared/components/cell/labelCellItem'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import { toLabelItems } from '@/monitoring/shared/labels'
import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'

const props = defineProps<{
  labels: Record<string, LabelValue>
  limit?: number | undefined
  /** The filter a click on a label narrows the listing to; without it the labels are plain. */
  filterBy?: ((item: LabelCellItem) => ColumnCondition) | undefined
}>()

const items = computed(() => toLabelItems(props.labels))
</script>

<template>
  <OverviewChips :items="items" :limit="limit" :filter-by="filterBy" />
</template>
