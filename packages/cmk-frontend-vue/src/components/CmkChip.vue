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
      small: 'cmk-chip-size-small',
      medium: 'cmk-chip-size-medium',
      large: 'cmk-chip-size-large'
    },
    color: {
      default: 'cmk-chip-color-default',
      success: 'cmk-chip-color-success',
      warning: 'cmk-chip-color-warning',
      danger: 'cmk-chip-color-danger'
    },
    variant: {
      fill: 'cmk-chip-variant-fill',
      outline: 'cmk-chip-variant-outline'
    }
  },
  defaultVariants: {
    size: 'medium',
    color: 'default',
    variant: 'outline'
  }
})

export type Sizes = VariantProps<typeof propsCva>['size']
export type Colors = VariantProps<typeof propsCva>['color']
export type Variants = VariantProps<typeof propsCva>['variant']

export interface CmkChipProps {
  size?: Sizes
  color?: Colors
  variant?: Variants
  content: string
}

defineProps<CmkChipProps>()
</script>

<template>
  <span class="cmk-chip" :class="propsCva({ size, color, variant })">
    {{ content }}
  </span>
</template>

<style scoped>
.cmk-chip {
  border-radius: 4px;
  text-align: center;
  margin: 0 4px;
}

.cmk-chip-size-small {
  font-size: 10px;
  padding: 1px 3px;
}

.cmk-chip-size-medium {
  font-size: 12px;
  padding: 2px 4px;
}

.cmk-chip-size-large {
  font-size: 14px;
  padding: 4px 5px;
}

.cmk-chip-color-danger {
  --chip-color: var(--color-danger);
}

.cmk-chip-color-warning {
  --chip-color: var(--color-warning);
}

.cmk-chip-color-success {
  --chip-color: var(--success);
}

.cmk-chip-color-default {
  --chip-color: var(--font-color);
  --chip-fill-color: var(--color-midnight-grey-50);
}

.cmk-chip-variant-fill {
  background: var(--chip-fill-color, var(--chip-color));
  border: 1px solid var(--chip-fill-color, var(--chip-color));
  color: var(--white);
}

.cmk-chip-variant-outline {
  background: transparent;
  border: 1px solid var(--chip-color);
  color: var(--chip-color);
}

/* Special cases for better contrast with fill variant */
.cmk-chip-variant-fill.cmk-chip-color-success {
  color: var(--black);
}

.cmk-chip-variant-fill.cmk-chip-color-warning {
  color: var(--black);
}
</style>
