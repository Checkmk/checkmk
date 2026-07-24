<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { useTemplateRef } from 'vue'

const scrollContainerVariants = cva('', {
  variants: {
    type: {
      // The slimmer scrollbar of the two, fitting the compact scroll areas of
      // components (popups, dialogs, panels)
      inner: 'cmk-scroll-container--inner',
      // The global scrollbar design, defined in the theme css and sized for
      // page-level content areas
      outer: ''
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

const containerRef = useTemplateRef('containerRef')

defineExpose({ containerRef })
</script>

<template>
  <div
    ref="containerRef"
    :style="{ maxHeight, height, overflow: 'auto' }"
    :class="scrollContainerVariants({ type })"
  >
    <slot></slot>
  </div>
</template>

<style scoped>
.cmk-scroll-container--inner::-webkit-scrollbar {
  width: 8px;
}

/* Firefox-only, like the global scrollbar design: in Chromium a non-auto
   scrollbar-width would disable the ::-webkit-scrollbar styling */
@supports (-moz-appearance: none) {
  .cmk-scroll-container--inner {
    scrollbar-width: thin;
  }
}
</style>
