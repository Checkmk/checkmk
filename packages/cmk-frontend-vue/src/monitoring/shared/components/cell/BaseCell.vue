<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type CSSProperties, computed, inject, useSlots } from 'vue'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import {
  COLUMN_LAYOUT_KEY,
  type CellBreakpoints,
  type ColumnJustify,
  justifyToFlex,
  resolveBreakpoint
} from '../MonitoringTableContext'
import HighlightWrapper, { type CellHighlight } from './base/HighlightWrapper.vue'

export interface CellLink {
  href: string
  target: '_self' | '_blank' | string | undefined
  variant?: 'inline' | 'icon' | undefined
}

const props = defineProps<{
  columnId?: string | undefined
  breakpoints?: CellBreakpoints | undefined
  linkedTo?: CellLink | undefined
  highlight?: CellHighlight | undefined
  justify?: ColumnJustify | undefined
}>()

const slots = useSlots()

const columns = inject(COLUMN_LAYOUT_KEY, null)

const columnInfo = computed(() =>
  props.columnId ? (columns?.value.get(props.columnId) ?? null) : null
)

// Explicit prop wins; otherwise fall back to the column's alignment (meta.justify
// flows in through the layout), so the header and body align from one source.
const effectiveJustify = computed<ColumnJustify>(
  () => props.justify ?? columnInfo.value?.justify ?? 'left'
)
const justifyContent = computed(() => justifyToFlex(effectiveJustify.value))

const pinnedLeft = computed(() => columnInfo.value?.pinnedLeft ?? null)
const pinnedStyle = computed<CSSProperties>(() =>
  pinnedLeft.value !== null ? { position: 'sticky', left: `${pinnedLeft.value}px`, zIndex: 1 } : {}
)
const cellWidth = computed(() => columnInfo.value?.width ?? Number.POSITIVE_INFINITY)

const activeSlot = computed<string>(() => {
  if (props.breakpoints) {
    const ranked = Object.entries(props.breakpoints)
      .map(([name, value]) => [name, resolveBreakpoint(value)] as const)
      .sort((a, b) => b[1] - a[1])
    for (const [name, threshold] of ranked) {
      if (cellWidth.value >= threshold && slots[name]) {
        return name
      }
    }
  }
  return 'default'
})
</script>

<template>
  <td
    class="monitoring-base-cell"
    :class="{
      'monitoring-base-cell--pinned': pinnedLeft !== null,
      'monitoring-base-cell--last-pinned': columnInfo?.isLastPinned
    }"
    :style="pinnedStyle"
  >
    <a
      v-if="linkedTo && linkedTo.variant !== 'icon'"
      class="monitoring-base-cell__link"
      :href="linkedTo.href"
      :target="linkedTo.target"
    >
      <HighlightWrapper :highlight="highlight" :justify="effectiveJustify" :is-linked="true">
        <slot :name="activeSlot" />
      </HighlightWrapper>
    </a>
    <div v-else class="monitoring-base-cell__wrapper">
      <HighlightWrapper :highlight="highlight" :justify="effectiveJustify">
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
  text-align: v-bind(effectiveJustify);

  a {
    text-decoration: underline;
    color: var(--font-color) !important;

    &:hover {
      text-decoration: none;
    }
  }

  .monitoring-base-cell__link {
    display: flex;
    justify-content: v-bind(justifyContent);
  }

  .monitoring-base-cell__wrapper {
    display: flex;
    align-items: center;
    flex-direction: row;
    justify-content: v-bind(justifyContent);

    .monitoring-base-cell__link-icon {
      flex: 0 0 auto;
      margin: 0 var(--dimension-3) 0 var(--dimension-2);
    }
  }
}

.monitoring-base-cell--pinned {
  background: inherit;
}

.monitoring-base-cell--last-pinned::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 8px;
  transform: translateX(100%);
  pointer-events: none;
  background: linear-gradient(to right, rgb(0 0 0 / 30%), rgb(0 0 0 / 0%));
}
</style>
