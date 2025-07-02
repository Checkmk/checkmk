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
      inner: '', // Inner style is default and defined in global css via cmk-vue-app class
      outer: 'scroll-container--outer'
    }
  },
  defaultVariants: {
    type: 'inner'
  }
})

export type ScrollContainerVariants = VariantProps<typeof scrollContainerVariants>

export interface ScrollContainerProps {
  maxHeight?: string
  height?: string
  type?: ScrollContainerVariants['type']
}
const { type, maxHeight = '100%', height = '100%' } = defineProps<ScrollContainerProps>()
</script>

<template>
  <div :style="{ maxHeight, height, overflow: 'auto' }" :class="scrollContainerVariants({ type })">
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
  border: 0;
}
</style>
