<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkTag, { type Colors, type Sizes, type Variants } from '@/components/CmkTag.vue'

import BaseCell, { type CellLink } from './BaseCell.vue'

export interface NumberTagProps {
  size?: Sizes
  color?: Colors
  variant?: Variants
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
        :variant="tagProperties.variant"
        :size="tagProperties.size"
        :color="tagProperties.color"
        :content="valueString"
      />
      <template v-else>
        {{ valueString }}
      </template>
    </template>
  </BaseCell>
</template>
