<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { TabsTrigger } from 'radix-vue'

const propsCva = cva('', {
  variants: {
    variant: {
      default: 'cmk-tab__variant-default',
      info: 'cmk-tab__variant-info',
      success: 'cmk-tab__variant-success',
      warning: 'cmk-tab__variant-warning',
      error: 'cmk-tab__variant-error'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})

export type Variants = VariantProps<typeof propsCva>['variant']

export interface CmkTabProps {
  id: string
  disabled?: boolean | undefined
  variant?: Variants
}

defineProps<CmkTabProps>()
</script>

<template>
  <TabsTrigger
    :value="id"
    :disabled="!!disabled"
    as="li"
    class="cmk-tab__li"
    :class="propsCva({ variant })"
  >
    <slot />
  </TabsTrigger>
</template>

<style scoped>
.cmk-tab__li {
  display: flex;
  flex-direction: row;
  background: var(--ux-theme-0);
  padding: var(--spacing-half) var(--spacing) !important;
  border: 1px solid var(--ux-theme-7);
  font-weight: var(--font-weight-default);
  line-height: var(--form-field-height);
  border-right: 0 solid var(--ux-theme-0);

  &:first-of-type {
    border-top-left-radius: var(--border-radius);
  }

  &:last-of-type {
    border-top-right-radius: var(--border-radius);
    border-right: 1px solid var(--ux-theme-7);
  }

  &:hover {
    cursor: pointer;
    background: var(--ux-theme-2);
  }

  &:focus-visible {
    outline: none;
    border: 1px solid var(--success);
  }

  &[data-state='active'] {
    background: var(--ux-theme-7);
    font-weight: var(--font-weight-bold);
  }

  &[data-disabled] {
    opacity: 0.6;
    cursor: default;
    background: var(--ux-theme-0);
  }
}

.cmk-tab__variant-info {
  border-top: 1px solid var(--color-dark-blue-50);
  border-left: 1px solid var(--color-dark-blue-50);
  border-right: 1px solid var(--color-dark-blue-50) !important;
}

.cmk-tab__variant-success {
  border-top: 1px solid var(--color-corporate-green-50);
  border-left: 1px solid var(--color-corporate-green-50);
  border-right: 1px solid var(--color-corporate-green-50) !important;
}

.cmk-tab__variant-warning {
  border-top: 1px solid var(--color-yellow-50);
  border-left: 1px solid var(--color-yellow-50);
  border-right: 1px solid var(--color-yellow-50) !important;
}

.cmk-tab__variant-error {
  border-top: 1px solid var(--color-dark-red-50);
  border-left: 1px solid var(--color-dark-red-50);
  border-right: 1px solid var(--color-dark-red-50) !important;
}
</style>
