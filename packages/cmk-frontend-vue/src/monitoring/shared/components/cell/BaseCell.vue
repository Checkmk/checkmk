<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import { type CSSProperties, computed, inject, useSlots } from 'vue'

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

export type CellVerticalAlign = 'top' | 'middle'

const props = defineProps<{
  columnId?: string | undefined
  breakpoints?: CellBreakpoints | undefined
  linkedTo?: CellLink | undefined
  highlight?: CellHighlight | undefined
  justify?: ColumnJustify | undefined
  button?: boolean | undefined
  verticalAlign?: CellVerticalAlign | undefined
  noWrap?: boolean | undefined
}>()

const emit = defineEmits<{
  (event: 'click', payload: MouseEvent): void
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
  if (props.highlight && props.highlight.active !== false) {
    classes.push(`monitoring-base-cell__highlight--color-${props.highlight.color}`)
  }
  return classes
})

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
      'monitoring-base-cell--first-pinned-right': columnInfo?.isFirstPinnedRight,
      'monitoring-base-cell--vertical-middle': verticalAlign === 'middle',
      'monitoring-base-cell--no-wrap': noWrap === true
    }"
    :style="pinnedStyle"
  >
    <button
      v-if="button"
      type="button"
      class="monitoring-base-cell__button"
      @click="emit('click', $event)"
    >
      <div v-if="highlight" :class="highlightClasses" :style="highlightStyle">
        <slot :name="activeSlot" />
      </div>
      <div v-else class="monitoring-base-cell__plain">
        <slot :name="activeSlot" />
      </div>
      <CmkMultitoneIcon
        class="monitoring-base-cell__chevron"
        name="chevron-right"
        primary-color="font"
        size="small"
      />
    </button>
    <a
      v-else-if="linkedTo && linkedTo.variant !== 'icon'"
      class="monitoring-base-cell__link"
      :class="{ 'monitoring-base-cell__link--highlighted': highlight }"
      :href="linkedTo.href"
      :target="linkedTo.target"
    >
      <div v-if="highlight" :class="highlightClasses" :style="highlightStyle">
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
      <CmkIconLink
        v-if="linkedTo && linkedTo.variant === 'icon'"
        class="monitoring-base-cell__link-icon"
        name="external"
        size="small"
        :href="linkedTo.href"
        :target="linkedTo.target"
      />
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

  a.monitoring-base-cell__link--highlighted {
    text-decoration: none;

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

  .monitoring-base-cell__button {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    width: 100%;
    min-height: 31px;
    padding: 0;
    margin: 0;
    background: transparent;
    border: none;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;

    &:hover {
      background-color: var(--ux-theme-3);
    }

    &:focus-visible {
      outline: 1px solid var(--success);
      outline-offset: -1px;
    }

    .monitoring-base-cell__chevron {
      flex: 0 0 auto;
      align-self: center;
      margin-left: auto;
      margin-top: calc(-1 * var(--dimension-2));
      margin-right: var(--dimension-3);
      height: var(--dimension-6);
    }
  }

  .monitoring-base-cell__plain {
    padding: 5px var(--dimension-4);
  }
}

.monitoring-base-cell--vertical-middle {
  vertical-align: middle;

  .monitoring-base-cell__link,
  .monitoring-base-cell__wrapper,
  .monitoring-base-cell__button {
    align-items: center;
  }
}

.monitoring-base-cell--no-wrap {
  white-space: nowrap;
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
  --cell-highlight-bar-width: 2px;
  --cell-highlight-bar-height: var(--dimension-7);

  display: flex;
  box-sizing: border-box;
  width: fit-content;
  min-height: 31px;
  align-items: center;
  justify-content: v-bind(justifyContent);
  gap: var(--dimension-4);
  margin: 0 var(--dimension-3);
  color: var(--cell-highlight-font-color, inherit);
}

.monitoring-base-cell
  a.monitoring-base-cell__link--highlighted:hover
  .monitoring-base-cell__highlight {
  text-decoration: underline;
  text-decoration-color: currentcolor;
}

.monitoring-base-cell__highlight::after {
  content: '';
  flex: 0 0 auto;
  width: var(--cell-highlight-bar-width);
  height: var(--cell-highlight-bar-height);
  background: var(--cell-highlight-accent-color, transparent);
}

/* The accent bar holds across both themes; only the value adapts to its background. */
.monitoring-base-cell__highlight--color-default {
  --cell-highlight-accent-color: var(--color-mid-grey-30);
  --cell-highlight-font-color: var(--color-mid-grey-100);
}

.monitoring-base-cell__highlight--color-success {
  --cell-highlight-accent-color: var(--color-corporate-green-80);
  --cell-highlight-font-color: var(--color-corporate-green-80);
}

.monitoring-base-cell__highlight--color-warning {
  --cell-highlight-accent-color: var(--color-yellow-60);
  --cell-highlight-font-color: var(--color-yellow-80);
}

.monitoring-base-cell__highlight--color-danger {
  --cell-highlight-accent-color: var(--color-dark-red-60);
  --cell-highlight-font-color: var(--color-dark-red-70);
}

.monitoring-base-cell__highlight--color-unknown {
  --cell-highlight-accent-color: var(--color-orange-70);
  --cell-highlight-font-color: var(--color-orange-80);
}

.monitoring-base-cell__highlight--color-pending {
  --cell-highlight-accent-color: var(--color-mist-grey-80);
  --cell-highlight-font-color: var(--color-mist-grey-70);
}

body[data-theme='modern-dark'] {
  .monitoring-base-cell__highlight--color-default {
    --cell-highlight-font-color: var(--color-mid-grey-0);
  }

  .monitoring-base-cell__highlight--color-success {
    --cell-highlight-font-color: var(--color-corporate-green-60);
  }

  .monitoring-base-cell__highlight--color-warning {
    --cell-highlight-font-color: var(--color-yellow-50);
  }

  .monitoring-base-cell__highlight--color-danger {
    --cell-highlight-font-color: var(--color-dark-red-30);
  }

  .monitoring-base-cell__highlight--color-unknown {
    --cell-highlight-font-color: var(--color-orange-60);
  }

  .monitoring-base-cell__highlight--color-pending {
    --cell-highlight-font-color: var(--color-mist-grey-40);
  }
}
</style>
