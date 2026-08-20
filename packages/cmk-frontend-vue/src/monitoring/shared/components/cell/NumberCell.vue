<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import BaseCell, { type CellLink } from './BaseCell.vue'
import type { CellHighlight } from './base/highlight'

export interface NumberCellProps {
  value: number | undefined
  linkedTo?: CellLink | undefined
  decimals?: number | undefined
  highlight?: CellHighlight | undefined
  columnId?: string | undefined
}

const props = defineProps<NumberCellProps>()

const valueString = computed(() => {
  if (props.value === undefined) {
    return 'n/a' as TranslatedString
  }
  return props.value.toFixed(props.decimals ?? 0) as TranslatedString
})
</script>

<template>
  <BaseCell :column-id="columnId" :linked-to="linkedTo" :highlight="highlight">
    <template #default>{{ valueString }}</template>
  </BaseCell>
</template>
