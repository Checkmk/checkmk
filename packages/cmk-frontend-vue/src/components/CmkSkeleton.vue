<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const propsSkeleton = cva('', {
  variants: {
    type: {
      box: 'box',
      h1: 'h1',
      h2: 'h2',
      h3: 'h3',
      text: 'text',
      'info-text': 'info-text',
      'icon-xsmall': 'icon-xsmall',
      'icon-small': 'icon-small',
      'icon-medium': 'icon-medium',
      'icon-large': 'icon-large',
      'icon-xlarge': 'icon-xlarge',
      'icon-xxlarge': 'icon-xxlarge',
      'icon-xxxlarge': 'icon-xxxlarge'
    }
  },
  defaultVariants: {
    type: 'box'
  }
})

export type SkeletonType = VariantProps<typeof propsSkeleton>['type']
defineProps<{ type?: SkeletonType | undefined }>()
</script>

<template>
  <div class="cmk-skeleton" :class="propsSkeleton({ type })">
    <slot />
  </div>
</template>

<style scoped>
.cmk-skeleton {
  display: inline-block;
  position: relative;
  overflow: hidden;
  background-color: var(--color-skeleton);

  &::after {
    position: absolute;
    inset: 0;
    transform: translateX(-100%);
    background: linear-gradient(
      90deg,
      var(--color-skeleton-shimmer-0) 0,
      var(--color-skeleton-shimmer-1) 20%,
      var(--color-skeleton-shimmer-2) 60%,
      var(--color-skeleton-shimmer-0)
    );
    animation: shimmer 3s infinite;
    content: '';
  }

  /* stylelint-disable checkmk/vue-bem-naming-convention */

  &.box {
    height: 100%;
    width: 100%;
  }

  &.h1,
  &.h2,
  &.h3,
  &.text,
  &.info-text {
    min-width: 50px;
    border-radius: var(--border-radius);
  }

  &.h1 {
    height: var(--font-size-xxlarge);
  }

  &.h2 {
    height: var(--font-size-xlarge);
  }

  &.h3 {
    height: var(--font-size-large);
  }

  &.text {
    height: var(--font-size-normal);
  }

  &.info-text {
    height: var(--font-size-small);
  }

  &.icon-xsmall,
  &.icon-small,
  &.icon-medium,
  &.icon-large,
  &.icon-xlarge,
  &.icon-xxlarge,
  &.icon-xxxlarge {
    border-radius: 99px;
  }

  &.icon-xsmall {
    width: 10px;
    height: 10px;
  }

  &.icon-small {
    width: 12px;
    height: 12px;
  }

  &.icon-medium {
    width: 15px;
    height: 15px;
  }

  &.icon-large {
    width: 18px;
    height: 18px;
  }

  &.icon-xlarge {
    width: 20px;
    height: 20px;
  }

  &.icon-xxlarge {
    width: 32px;
    height: 32px;
  }

  &.icon-xxxlarge {
    width: 77px;
    height: 77px;
  }
}

@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>
