<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
const cmkSpaceVariants = cva('cmk-space', {
  variants: {
    direction: {
      horizontal: 'cmk-space--direction-horizontal',
      vertical: 'cmk-space--direction-vertical'
    },
    size: {
      small: 'cmk-space--size-small',
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
.cmk-space {
  flex-shrink: 0;
}

.cmk-space--direction-horizontal {
  display: inline-block;

  &.cmk-space--size-medium {
    width: var(--spacing);
  }
  &.cmk-space--size-small {
    width: var(--spacing-half);
  }
}

.cmk-space--direction-vertical {
  &.cmk-space--size-medium {
    height: var(--spacing);
  }

  &.cmk-space--size-small {
    height: var(--spacing-half);
  }
}
</style>
