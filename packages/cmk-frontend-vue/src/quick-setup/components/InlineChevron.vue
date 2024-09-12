<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const inlineChevronVariants = cva('', {
  variants: {
    variant: {
      bottom: 'qs-inline-chevron--bottom',
      left: 'qs-inline-chevron--left',
      right: 'qs-inline-chevron--right'
    }
  },
  defaultVariants: {
    variant: 'bottom'
  }
})
type InlineChevronVariants = VariantProps<typeof inlineChevronVariants>

interface InlineChevronProps {
  /**@property {InlineChevronVariants['variant']} variant - The chevron's direction */
  variant: InlineChevronVariants['variant']
}

defineProps<InlineChevronProps>()
</script>

<template>
  <span :class="['qs-inline-chevron', inlineChevronVariants({ variant })]" />
</template>

<style scoped>
.qs-inline-chevron {
  display: inline-block;
  width: 8px;
  margin-right: var(--spacing-half);

  &::before {
    border-color: var(--success-dimmed);
    border-style: solid;
    border-width: 1px 1px 0 0;
    content: '';
    display: inline-block;
    width: 5px;
    height: 5px;
    position: relative;
    top: 0.15em;
    transform: rotate(-45deg);
    vertical-align: top;
  }

  &.qs-inline-chevron--bottom {
    padding-left: 3px;

    &:before {
      top: 2px;
      transform: rotate(135deg);
      transition: transform 100ms linear;
    }
  }

  &.qs-inline-chevron--left:before {
    left: 0.25em;
    transform: rotate(-135deg);
    transition: transform 100ms linear;
  }

  &.qs-inline-chevron--right:before {
    top: 4px;
    left: 0;
    margin-bottom: 16px;
    transform: rotate(45deg);
    transition: transform 100ms linear;
  }
}
</style>
