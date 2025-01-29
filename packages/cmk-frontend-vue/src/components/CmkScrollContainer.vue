<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
const scrollContainerVariants = cva('', {
  variants: {
    type: {
      inner: 'scroll-container--inner',
      outer: 'scroll-container--outer'
    }
  },
  defaultVariants: {
    type: 'inner'
  }
})
export type ScrollContainerVariants = VariantProps<typeof scrollContainerVariants>

interface ScrollContainerProps {
  type?: ScrollContainerVariants['type']
}
defineProps<ScrollContainerProps>()
</script>

<template>
  <div class="scroll-container" :class="scrollContainerVariants({ type })">
    <slot></slot>
  </div>
</template>

<style scoped>
.scroll-container {
  display: inline-block;
}

.scroll-container--outer {
  overflow: auto;
  height: 100%;
}

.scroll-container--outer > *:nth-child(1)::-webkit-scrollbar {
  width: 10px;
}

.scroll-container--outer > *:nth-child(1)::-webkit-scrollbar-track {
  background: transparent;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.scroll-container--outer > *:nth-child(1)::-webkit-scrollbar-thumb {
  background-color: var(--scrollbar-color);
  border-radius: 16px;
}

.scroll-container--inner {
  height: 100%;
}

.scroll-container--inner > *:nth-child(1)::-webkit-scrollbar {
  width: 8px;
}

.scroll-container--inner > *:nth-child(1)::-webkit-scrollbar-track {
  background: var(--ux-theme-6);
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.scroll-container--inner > *:nth-child(1)::-webkit-scrollbar-thumb {
  background-color: var(--scrollbar-color);
  border-radius: 16px;
  border: 3px solid var(--ux-theme-6);
}

.scroll-container--inner > *:nth-child(1)::-webkit-scrollbar-corner {
  background-color: var(--ux-theme-6);
}
</style>
