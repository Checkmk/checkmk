<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

const cmkLinkCardContainerOrientation = cva('', {
  variants: {
    orientation: {
      vertical: 'cmk-link-card-container--vertical',
      horizontal: 'cmk-link-card-container--horizontal'
    }
  },
  defaultVariants: {
    orientation: 'vertical'
  }
})

export type CmkLinkCardOrientation = VariantProps<
  typeof cmkLinkCardContainerOrientation
>['orientation']

interface CmkLinkCardContainerProps {
  orientation?: CmkLinkCardOrientation
}

defineProps<CmkLinkCardContainerProps>()
</script>

<template>
  <div class="cmk-link-card-container" :class="cmkLinkCardContainerOrientation({ orientation })">
    <slot />
  </div>
</template>

<style scoped>
.cmk-link-card-container {
  display: flex;
  gap: var(--dimension-4);
  flex-direction: column;

  &.cmk-link-card-container--horizontal {
    flex-direction: row;
  }
}
</style>
