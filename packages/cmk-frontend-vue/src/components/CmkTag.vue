<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

import type { TranslatedString } from '@/lib/i18nString'

const propsCva = cva('', {
  variants: {
    size: {
      small: 'cmk-tag--size-small',
      medium: 'cmk-tag--size-medium',
      large: 'cmk-tag--size-large'
    },
    color: {
      default: 'cmk-tag--color-default',
      success: 'cmk-tag--color-success',
      warning: 'cmk-tag--color-warning',
      danger: 'cmk-tag--color-danger'
    },
    variant: {
      fill: 'cmk-tag--variant-fill',
      outline: 'cmk-tag--variant-outline'
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

export interface CmkTagProps {
  size?: Sizes
  color?: Colors
  variant?: Variants
  content: TranslatedString
}

defineProps<CmkTagProps>()
</script>

<template>
  <span class="cmk-tag" :class="propsCva({ size, color, variant })">
    {{ content }}
  </span>
</template>

<style scoped>
.cmk-tag {
  border-radius: 4px;
  text-align: center;
  margin: 0 4px;
}

.cmk-tag--size-small {
  font-size: 10px;
  padding: 1px 3px;
}

.cmk-tag--size-medium {
  font-size: 12px;
  padding: 2px 4px;
}

.cmk-tag--size-large {
  font-size: 14px;
  padding: 4px 5px;
}

.cmk-tag--color-danger {
  --tag-color: var(--color-danger);
}

.cmk-tag--color-warning {
  --tag-color: var(--color-warning);
}

.cmk-tag--color-success {
  --tag-color: var(--success);
}

.cmk-tag--color-default {
  --tag-color: var(--font-color);
  --tag-fill-color: var(--color-midnight-grey-50);
}

.cmk-tag--variant-fill {
  background: var(--tag-fill-color, var(--tag-color));
  border: 1px solid var(--tag-fill-color, var(--tag-color));
  color: var(--white);
}

.cmk-tag--variant-outline {
  background: transparent;
  border: 1px solid var(--tag-color);
  color: var(--tag-color);
}

/* Special cases for better contrast with fill variant */
.cmk-tag--variant-fill.cmk-tag--color-success {
  color: var(--black);
}

.cmk-tag--variant-fill.cmk-tag--color-warning {
  color: var(--black);
}
</style>
