<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import BaseCell, { type CellLink } from './BaseCell.vue'
import { type CellHighlight } from './base/HighlightWrapper.vue'

export interface NumberCellProps {
  value: number
  linkedTo?: CellLink | undefined
  decimals?: number | undefined
  highlight?: CellHighlight | undefined
  columnId?: string | undefined
}

const props = defineProps<NumberCellProps>()

const valueString = computed(() => {
  return props.value.toFixed(props.decimals ?? 0) as TranslatedString
})
</script>

<template>
  <BaseCell :column-id="columnId" :highlight="highlight" :linked-to="linkedTo">
    <template #default>
      {{ valueString }}
    </template>
  </BaseCell>
</template>
