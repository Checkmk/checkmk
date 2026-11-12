<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { LabelValue } from '@/monitoring/shared/api/types'
import type { ItemAction, LabelCellItem } from '@/monitoring/shared/components/cell/labelCellItem'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import { toLabelItems } from '@/monitoring/shared/labels'

const props = defineProps<{
  labels: Record<string, LabelValue>
  limit?: number | undefined
  action?: ItemAction | undefined
}>()

defineEmits<{ select: [item: LabelCellItem] }>()

const items = computed(() => toLabelItems(props.labels))
</script>

<template>
  <OverviewChips :items="items" :limit="limit" :action="action" @select="$emit('select', $event)" />
</template>
