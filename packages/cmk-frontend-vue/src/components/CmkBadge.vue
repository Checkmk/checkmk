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
      small: 'cmk-badge-small',
      medium: 'cmk-badge-medium',
      large: 'cmk-badge-large'
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

export interface CmkBadgeProps {
  size?: Sizes
  color?: Colors
}

defineProps<CmkBadgeProps>()
</script>

<template>
  <div class="cmk-badge" :class="propsCva({ size, color })">
    <slot />
  </div>
</template>

<style scoped>
.cmk-badge {
  border-radius: 99999px;
  border: 1px solid var(--custom-scroll-bar-thumb-color);
  color: var(--custom-scroll-bar-thumb-color);
  text-align: center;
  margin: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.cmk-badge-small {
  font-size: 10px;
  width: 12px;
  height: 12px;
  max-width: 12px;
}

.cmk-badge-medium {
  font-size: 12px;
  width: 18px;
  height: 18px;
  max-width: 18px;
}

.cmk-badge-large {
  font-size: 14px;
  width: 24px;
  height: 24px;
  max-width: 24px;
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
