<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const propsCva = cva('cmk-heading', {
  variants: {
    type: {
      h1: 'cmk-heading--h1',
      h2: 'cmk-heading--h2',
      h3: 'cmk-heading--h3',
      h4: 'cmk-heading--h4'
    }
  },
  defaultVariants: {
    type: 'h1'
  }
})

export type HeadingType = VariantProps<typeof propsCva>['type']

export interface CmkHeadingProps {
  type?: HeadingType
  onClick?: (() => void) | null
}

defineProps<CmkHeadingProps>()
</script>

<template>
  <component
    :is="type || 'h1'"
    :class="[propsCva({ type }), { 'cmk-heading--clickable': onClick!! }]"
    @click="onClick"
  >
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
  font-size: var(--font-size-xlarge);
}

.cmk-heading--h3 {
  font-size: var(--font-size-large);
}

.cmk-heading--h4 {
  font-size: var(--font-size-normal);
}

.cmk-heading--clickable {
  cursor: pointer;
}
</style>
