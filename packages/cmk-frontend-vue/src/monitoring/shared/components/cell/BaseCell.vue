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
import type { CellHighlight } from './base/highlight'

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
const pinnedRight = computed(() => columnInfo.value?.pinnedRight ?? null)
const pinnedStyle = computed<CSSProperties>(() => {
  if (pinnedLeft.value !== null) {
    return { position: 'sticky', left: `${pinnedLeft.value}px`, zIndex: 1 }
  }
  if (pinnedRight.value !== null) {
    return { position: 'sticky', right: `${pinnedRight.value}px`, zIndex: 1 }
  }
  return {}
})
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

const highlightClasses = computed<string[]>(() => {
  const classes = ['monitoring-base-cell__highlight']
  if (props.highlight) {
    classes.push(
      `monitoring-base-cell__highlight--${props.highlight.type}`,
      `monitoring-base-cell__highlight--color-${props.highlight.color}`
    )
  }
  return classes
})

const linkedHighlightClasses = computed<string[]>(() =>
  props.highlight
    ? [...highlightClasses.value, 'monitoring-base-cell__highlight--hover']
    : highlightClasses.value
)

const highlightStyle = computed<CSSProperties>(() =>
  props.highlight?.minWidth !== undefined ? { minWidth: `${props.highlight.minWidth}px` } : {}
)
</script>

<template>
  <td
    class="monitoring-base-cell"
    :class="{
      'monitoring-base-cell--pinned': pinnedLeft !== null || pinnedRight !== null,
      'monitoring-base-cell--last-pinned': columnInfo?.isLastPinned,
      'monitoring-base-cell--first-pinned-right': columnInfo?.isFirstPinnedRight
    }"
    :style="pinnedStyle"
  >
    <a
      v-if="linkedTo && linkedTo.variant !== 'icon'"
      class="monitoring-base-cell__link"
      :href="linkedTo.href"
      :target="linkedTo.target"
    >
      <div v-if="highlight" :class="linkedHighlightClasses" :style="highlightStyle">
        <slot :name="activeSlot" />
      </div>
      <div v-else class="monitoring-base-cell__plain">
        <slot :name="activeSlot" />
      </div>
    </a>
    <div v-else class="monitoring-base-cell__wrapper">
      <div v-if="highlight" :class="highlightClasses" :style="highlightStyle">
        <slot :name="activeSlot" />
      </div>
      <div v-else class="monitoring-base-cell__plain">
        <slot :name="activeSlot" />
      </div>
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
  vertical-align: top;
  min-height: 31px;
  line-height: 21px;
  text-align: v-bind(effectiveJustify);
  background-color: var(--ux-theme-2);

  a {
    text-decoration: underline;
    color: var(--font-color) !important;

    &:hover {
      text-decoration: none;
    }
  }

  .monitoring-base-cell__link {
    display: flex;
    align-items: flex-start;
    min-height: 31px;
    justify-content: v-bind(justifyContent);
  }

  .monitoring-base-cell__wrapper {
    display: flex;
    align-items: flex-start;
    flex-direction: row;
    min-height: 31px;
    justify-content: v-bind(justifyContent);

    .monitoring-base-cell__link-icon {
      flex: 0 0 auto;
      margin: 0 var(--dimension-3) 0 var(--dimension-2);
    }
  }

  .monitoring-base-cell__plain {
    padding: 5px var(--dimension-4);
  }
}

.monitoring-base-cell--pinned {
  background: var(--ux-theme-1);
  box-shadow: 0 0 0 1px var(--ux-theme-4);
}

.monitoring-base-cell--last-pinned::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 2px;
  pointer-events: none;
  background: var(--default-border-color);
}

.monitoring-base-cell--first-pinned-right::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 2px;
  pointer-events: none;
  background: var(--default-border-color);
}

.monitoring-base-cell__highlight {
  margin: var(--dimension-2) var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  border-radius: var(--border-radius);
  border-width: 1px;
  border-style: solid;
  box-sizing: border-box;
  border-color: transparent;
  width: fit-content;
  display: flex;
  flex-direction: row;
  align-items: center;
  align-content: center;
  gap: var(--dimension-3);

  &.monitoring-base-cell__highlight--full {
    margin: 0;
    width: 100%;
    padding: var(--dimension-3) var(--dimension-3);
    border-radius: 0;
    justify-content: v-bind(justifyContent);
  }

  &.monitoring-base-cell__highlight--color-default {
    border-color: var(--color-midnight-grey-50);
    background-color: var(--color-midnight-grey-50);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-base-cell__highlight--color-success {
    border-color: var(--success);
    background-color: var(--success);
    color: var(--black);
    text-decoration-color: var(--black) !important;
  }

  &.monitoring-base-cell__highlight--color-warning {
    border-color: var(--color-warning);
    background-color: var(--color-warning);
    color: var(--black);
    text-decoration-color: var(--black);
  }

  &.monitoring-base-cell__highlight--color-danger {
    border-color: var(--color-danger);
    background-color: var(--color-danger);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-base-cell__highlight--color-info {
    border-color: var(--color-dark-blue-50);
    background-color: var(--color-dark-blue-50);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-base-cell__highlight--outline {
    background-color: transparent;
    color: var(--font-color) !important;
  }

  &.monitoring-base-cell__highlight--hover {
    position: relative;
    overflow: hidden;
    text-decoration: underline;

    &::after {
      content: '';
      position: absolute;
      width: 100%;
      height: 100%;
      opacity: 0.1;
      left: 0;
      top: 0;
    }

    &:hover {
      text-decoration: none;

      &::after {
        background: var(--white);
      }
    }
  }
}
</style>
