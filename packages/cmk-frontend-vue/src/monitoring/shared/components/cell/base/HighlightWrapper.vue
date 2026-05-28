<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

export interface CellHighlight {
  type: 'inline' | 'outline' | 'full'
  color: 'default' | 'success' | 'warning' | 'danger' | 'info'
}

const props = defineProps<{
  highlight?: CellHighlight | undefined
  isLinked?: boolean | undefined
}>()

const highlightClass = computed<string | null>(() => {
  if (props.highlight) {
    const hClass = [
      `monitoring-highlight-wrapper--${props.highlight.type ?? 'inline'}`,
      `monitoring-highlight-wrapper--color-${props.highlight.color ?? 'none'}`
    ]

    if (props.isLinked) {
      hClass.push('monitoring-highlight-wrapper--hover')
    }

    return hClass.join(' ')
  }

  return ''
})
</script>

<template>
  <div class="monitoring-highlight-wrapper" :class="highlightClass">
    <slot />
  </div>
</template>

<style scoped>
.monitoring-highlight-wrapper {
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

  &.monitoring-highlight-wrapper--full {
    margin: 0;
    width: auto;
    padding: var(--dimension-3) var(--dimension-3);
    border-radius: 0;
  }

  &.monitoring-highlight-wrapper--color-default {
    border-color: var(--color-midnight-grey-50);
    background-color: var(--color-midnight-grey-50);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-highlight-wrapper--color-success {
    border-color: var(--success);
    background-color: var(--success);
    color: var(--black);
    text-decoration-color: var(--black) !important;
  }

  &.monitoring-highlight-wrapper--color-warning {
    border-color: var(--color-warning);
    background-color: var(--color-warning);
    color: var(--black);
    text-decoration-color: var(--black);
  }

  &.monitoring-highlight-wrapper--color-danger {
    border-color: var(--color-danger);
    background-color: var(--color-danger);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-highlight-wrapper--color-info {
    border-color: var(--color-dark-blue-50);
    background-color: var(--color-dark-blue-50);
    color: var(--white);
    text-decoration-color: var(--white);
  }

  &.monitoring-highlight-wrapper--outline {
    background-color: transparent;
    color: var(--font-color) !important;
  }

  &.monitoring-highlight-wrapper--hover {
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
