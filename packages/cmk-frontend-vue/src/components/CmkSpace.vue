<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
const cmkSpaceVariants = cva('', {
  variants: {
    direction: {
      horizontal: 'cmk-space--direction-horizontal'
    },
    size: {
      medium: 'cmk-space--size-medium'
    }
  },
  defaultVariants: {
    direction: 'horizontal',
    size: 'medium'
  }
})
export type CmkSpaceVariants = VariantProps<typeof cmkSpaceVariants>

interface CmkSpaceProps {
  size?: CmkSpaceVariants['size']
  direction?: CmkSpaceVariants['direction']
}
defineProps<CmkSpaceProps>()
</script>

<template>
  <div :class="cmkSpaceVariants({ size, direction })" />
</template>

<style scoped>
.cmk-space--direction-horizontal {
  display: inline-block;
  &.cmk-space--size-medium {
    width: var(--spacing);
  }
}
</style>
