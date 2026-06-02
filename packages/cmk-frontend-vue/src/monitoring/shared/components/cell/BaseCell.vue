<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject, ref, useSlots } from 'vue'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import {
  type BreakpointValue,
  type CellBreakpoints,
  MONITORING_TABLE_WIDTH,
  resolveBreakpoint
} from '../MonitoringTableContext'
import HighlightWrapper, { type CellHighlight } from './base/HighlightWrapper.vue'

export interface CellLink {
  href: string
  target: '_self' | '_blank' | string | undefined
  variant?: 'inline' | 'icon' | undefined
}

const props = defineProps<{
  breakpoints?: CellBreakpoints | undefined
  hideBelow?: BreakpointValue | undefined
  linkedTo?: CellLink | undefined
  highlight?: CellHighlight | undefined
}>()

const slots = useSlots()
const containerWidth = inject(MONITORING_TABLE_WIDTH, ref<number>(Number.POSITIVE_INFINITY))

const visible = computed(() => {
  if (props.hideBelow === undefined) {
    return true
  }
  return containerWidth.value >= resolveBreakpoint(props.hideBelow)
})

const activeSlot = computed<string>(() => {
  if (props.breakpoints) {
    const ranked = Object.entries(props.breakpoints)
      .map(([name, value]) => [name, resolveBreakpoint(value)] as const)
      .sort((a, b) => b[1] - a[1])
    for (const [name, threshold] of ranked) {
      if (containerWidth.value >= threshold && slots[name]) {
        return name
      }
    }
  }
  return 'default'
})
</script>

<template>
  <td v-if="visible" class="monitoring-base-cell">
    <a
      v-if="linkedTo && linkedTo.variant !== 'icon'"
      :href="linkedTo.href"
      :target="linkedTo.target"
    >
      <HighlightWrapper :highlight="highlight" :is-linked="true">
        <slot :name="activeSlot" />
      </HighlightWrapper>
    </a>
    <div v-else class="monitoring-base-cell__wrapper">
      <HighlightWrapper :highlight="highlight">
        <slot :name="activeSlot" />
      </HighlightWrapper>
      <a
        v-if="linkedTo && linkedTo.variant === 'icon'"
        :href="linkedTo.href"
        :target="linkedTo.target"
      >
        <CmkIcon class="monitoring-base-cell__link-icon" name="external" size="small" />
      </a>
    </div>
  </td>
</template>

<style scoped>
.monitoring-base-cell {
  vertical-align: middle;
  height: 24px;

  a {
    text-decoration: underline;
  }

  .monitoring-base-cell__wrapper {
    display: flex;
    align-items: center;
    flex-direction: row;

    .monitoring-base-cell__link-icon {
      flex: 0 0 auto;
      margin: 0 var(--dimension-3) 0 var(--dimension-2);
    }
  }
}
</style>
