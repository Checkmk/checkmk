<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getIsItemExpandedCallback } from './trigger-item'

const isItemExpanded = getIsItemExpandedCallback()

defineProps<{
  value: string
}>()
</script>

<template>
  <span
    class="cmk-accordion-item-state-indicator"
    :class="{ open: typeof value !== 'undefined' && isItemExpanded(value) }"
  ></span>
</template>

<style scoped>
.cmk-accordion-item-state-indicator {
  width: 16px;
  height: 16px;
  &:after {
    border-color: var(--help-text-font-color);
    border-style: solid;
    border-width: 2px 2px 0 0;
    content: '';
    display: inline-block;
    width: 6px;
    height: 6px;
    position: relative;
    transform: rotate(45deg);
    top: -3px;
    transition:
      transform 0.3s ease-in-out,
      top 0.3s ease-in-out;
  }
}

.open {
  &:after {
    transform: rotate(135deg);
    top: -3px;
    transition:
      transform 0.3s ease-out,
      top 0.3s ease-out;
  }
}
</style>
