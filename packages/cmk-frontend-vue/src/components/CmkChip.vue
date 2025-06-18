<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

const propsCva = cva('', {
  variants: {
    size: {
      small: 'small',
      medium: 'medium',
      large: 'large'
    },
    color: {
      default: 'cmk-badge-default',
      success: 'cmk-badge-success',
      warning: 'cmk-badge-warning',
      danger: 'cmk-badge-danger'
    }
  },
  defaultVariants: {
    size: 'medium',
    color: 'default'
  }
})

export type Sizes = VariantProps<typeof propsCva>['size']
export type Colors = VariantProps<typeof propsCva>['color']

export interface CmkChipProps {
  size?: Sizes
  color?: Colors
  content: string
}

defineProps<CmkChipProps>()
</script>

<template>
  <span class="cmk-chip" :class="propsCva({ size, color })">
    {{ content }}
  </span>
</template>

<style scoped>
.cmk-chip {
  border-radius: 99999px;
  border: 1px solid var(--custom-scroll-bar-thumb-color);
  color: var(--custom-scroll-bar-thumb-color);
  text-align: center;
  margin: 0 4px;
}

.small {
  font-size: 10px;
  padding: 1px 5px;
}

.medium {
  font-size: 12px;
  padding: 3px 8px;
}

.large {
  font-size: 14px;
  padding: 5px 10px;
}

.cmk-badge-danger {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: var(--white);
}

.cmk-badge-warning {
  background: var(--color-warning);
  border-color: var(--color-warning);
}

.cmk-badge-success {
  background: var(--success);
  border-color: var(--success);
  color: var(--black);
}
</style>
