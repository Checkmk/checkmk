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
    },
    type: {
      fill: 'cmk-badge-fill',
      outline: 'cmk-badge-outline'
    },
    shape: {
      default: 'cmk-badge-default-shape',
      circle: 'cmk-badge-circle'
    }
  },
  defaultVariants: {
    size: 'medium',
    color: 'default',
    type: 'outline',
    shape: 'default'
  }
})

export type Sizes = VariantProps<typeof propsCva>['size']
export type Colors = VariantProps<typeof propsCva>['color']
export type Types = VariantProps<typeof propsCva>['type']
export type Shapes = VariantProps<typeof propsCva>['shape']

export interface CmkBadgeProps {
  size?: Sizes
  color?: Colors
  type?: Types
  shape?: Shapes
}

defineProps<CmkBadgeProps>()
</script>

<template>
  <div class="cmk-badge" :class="propsCva({ size, color, type, shape })">
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
  padding: 2px;
}

.cmk-badge-small {
  font-size: 10px;
  min-width: 12px;
  width: auto;
  height: 12px;
}

.cmk-badge-medium {
  font-size: 12px;
  min-width: 18px;
  width: auto;
  height: 18px;
}

.cmk-badge-large {
  font-size: 14px;
  min-width: 24px;
  width: auto;
  height: 24px;
}

.cmk-badge-default {
  background: var(--custom-scroll-bar-thumb-color);
  border-color: var(--custom-scroll-bar-thumb-color);
  color: var(--white);
}

.cmk-badge-danger {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: var(--white);
}

.cmk-badge-warning {
  background: var(--color-warning);
  border-color: var(--color-warning);
  color: var(--black);
}

.cmk-badge-success {
  background: var(--success);
  border-color: var(--success);
  color: var(--black);
}

.cmk-badge-outline {
  background: transparent;
  &.cmk-badge-default {
    color: var(--custom-scroll-bar-thumb-color);
  }

  &.cmk-badge-warning {
    color: var(--color-warning);
  }

  &.cmk-badge-danger {
    color: var(--color-danger);
  }

  &.cmk-badge-success {
    color: var(--success);
  }
}

.cmk-badge-fill {
  border-color: transparent;
}

.cmk-badge-circle {
  &.cmk-badge-small {
    max-width: 12px;
  }

  &.cmk-badge-medium {
    max-width: 18px;
  }

  &.cmk-badge-large {
    max-width: 24px;
  }
}
</style>
