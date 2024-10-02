<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const loadingIconVariants = cva('', {
  variants: {
    size: {
      xl: '32px',
      lg: '20px'
    }
  },
  defaultVariants: {
    size: 'xl'
  }
})
type LoadingIconVariants = VariantProps<typeof loadingIconVariants>

interface LoadingIconProps {
  /** @property {LoadingIconVariants['size']} size - Height of the loading icon */
  size?: LoadingIconVariants['size']
}
defineProps<LoadingIconProps>()
</script>

<template>
  <img
    src="themes/facelift/images/load_graph.png"
    alt="Loading"
    aria-label="Loading"
    class="qs-loading-icon"
  />
</template>

<style scoped>
.qs-loading-icon {
  margin-right: 8px;
  height: v-bind('loadingIconVariants({ size })');
}
</style>
