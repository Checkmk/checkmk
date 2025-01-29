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
  maxHeight?: string
  type?: ScrollContainerVariants['type']
}
const { type, maxHeight = '100%' } = defineProps<ScrollContainerProps>()
</script>

<template>
  <div :style="{ maxHeight, overflow: 'auto' }" :class="scrollContainerVariants({ type })">
    <slot></slot>
  </div>
</template>

<style scoped>
.scroll-container--outer::-webkit-scrollbar {
  width: 10px;
}

.scroll-container--outer::-webkit-scrollbar-track {
  background: transparent;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.scroll-container--outer::-webkit-scrollbar-thumb {
  background-color: var(--scrollbar-color);
  border-radius: 16px;
}

.scroll-container--inner::-webkit-scrollbar {
  width: 8px;
}

.scroll-container--inner::-webkit-scrollbar-track {
  background: var(--ux-theme-6);
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.scroll-container--inner::-webkit-scrollbar-thumb {
  background-color: var(--scrollbar-color);
  border-radius: 16px;
  border: 3px solid var(--ux-theme-6);
}

.scroll-container--inner::-webkit-scrollbar-corner {
  background-color: var(--ux-theme-6);
}
</style>
