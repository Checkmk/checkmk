<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

const propsCva = cva('cmk-heading', {
  variants: {
    type: {
      h1: 'cmk-heading--h1',
      h2: 'cmk-heading--h2'
    }
  },
  defaultVariants: {
    type: 'h1'
  }
})

export type HeadingType = VariantProps<typeof propsCva>['type']

export interface CmkHeadingProps {
  type?: HeadingType
}

const props = defineProps<CmkHeadingProps>()
</script>

<template>
  <component :is="props.type" :class="propsCva({ type })">
    <slot />
  </component>
</template>

<style scoped>
.cmk-heading {
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  margin: 0;
}

.cmk-heading--h1 {
  font-size: var(--font-size-xxlarge);
}

.cmk-heading--h2 {
  font-size: var(--font-size-normal);
}
</style>
