<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

const sizes = cva('', {
  variants: {
    size: {
      small: 'small',
      medium: 'medium',
      large: 'large'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type Sizes = VariantProps<typeof sizes>['size']

export interface CmkChipProps {
  size?: Sizes
  content: string
}

defineProps<CmkChipProps>()
</script>

<template>
  <span class="cmk-chip" :class="sizes({ size })">
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
</style>
