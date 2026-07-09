<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkTag, { type Colors, type Sizes, type Variants } from '@/components/CmkTag.vue'

import { type ColumnJustify, justifyToFlex } from '../MonitoringTableContext'
import BaseCell, { type CellLink } from './BaseCell.vue'

export interface NumberTagProps {
  size?: Sizes
  color?: Colors
  variant?: Variants
  minWidth?: number | undefined
  justify?: ColumnJustify | undefined
}

export interface NumberCellProps {
  value: number
  linkedTo?: CellLink | undefined
  decimals?: number | undefined
  tagProperties?: NumberTagProps | undefined
  columnId?: string | undefined
}

const props = defineProps<NumberCellProps>()

const valueString = computed(() => {
  return props.value.toFixed(props.decimals ?? 0) as TranslatedString
})
</script>

<template>
  <BaseCell :column-id="columnId" :linked-to="linkedTo">
    <template #default>
      <CmkTag
        v-if="tagProperties"
        class="monitoring-number-cell__tag"
        :class="{ 'monitoring-number-cell--tag-fixed': tagProperties.minWidth }"
        :variant="tagProperties.variant"
        :size="tagProperties.size"
        :color="tagProperties.color"
        :content="valueString"
        :style="{
          'min-width': tagProperties.minWidth ? `${tagProperties.minWidth}px` : undefined,
          'justify-content': justifyToFlex(tagProperties.justify ?? 'right')
        }"
      />
      <template v-else>
        {{ valueString }}
      </template>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-number-cell__tag {
  margin: 0;
}

.monitoring-number-cell--tag-fixed {
  display: flex;
  box-sizing: border-box;
  height: 21px;
  align-items: center;
}
</style>
