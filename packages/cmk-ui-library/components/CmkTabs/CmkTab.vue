<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import { TabsTrigger } from 'reka-ui'

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
    <CmkMultitoneIcon
      v-if="variant === 'error'"
      name="error"
      :primary-color="{ custom: 'var(--status-icon-color-error)' }"
      size="medium"
      class="cmk-tab__error-icon"
    />
    <slot />
  </TabsTrigger>
</template>

<style scoped>
.cmk-tab__li {
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
  height: var(--dimension-9);
  background: var(--background-base);
  padding: 0 var(--dimension-6) !important;
  border: 1px solid var(--border-color-subtle);
  border-right-width: 0;
  border-bottom-color: var(--border-color-strong);
  font-weight: var(--font-weight-default);

  &:first-of-type {
    border-top-left-radius: var(--dimension-3);
  }

  &:last-of-type {
    border-top-right-radius: var(--dimension-3);
    border-right-width: 1px;
  }

  &:focus-visible {
    outline: none;
    border-color: var(--success);
  }

  &:hover:not([data-state='active']) {
    cursor: pointer;
    background: var(--background-hover);
  }

  &[data-state='active'] {
    height: var(--dimension-10);
    background: var(--background-subtle);
    border-right-width: 1px;
    border-bottom-width: 0;
    border-top-left-radius: var(--dimension-3);
    border-top-right-radius: var(--dimension-3);
    font-weight: var(--font-weight-bold);
  }

  &[data-state='active'].cmk-tab__variant-default {
    border-color: var(--border-color-strong);
  }

  &[data-state='active'] + & {
    border-left-width: 0;
  }

  &[data-disabled] {
    opacity: 0.6;
    cursor: default;
    background: var(--background-base);
  }
}

.cmk-tab__variant-info {
  border-top: 1px solid var(--status-border-color-info);
  border-left: 1px solid var(--status-border-color-info);
  border-right: 1px solid var(--status-border-color-info) !important;
}

.cmk-tab__variant-success {
  border-top: 1px solid var(--status-border-color-success);
  border-left: 1px solid var(--status-border-color-success);
  border-right: 1px solid var(--status-border-color-success) !important;
}

.cmk-tab__variant-warning {
  border-top: 1px solid var(--status-border-color-warning);
  border-left: 1px solid var(--status-border-color-warning);
  border-right: 1px solid var(--status-border-color-warning) !important;
}

.cmk-tab__variant-error {
  border-top: 1px solid var(--status-border-color-error);
  border-left: 1px solid var(--status-border-color-error);
  border-right: 1px solid var(--status-border-color-error) !important;
}

.cmk-tab__error-icon {
  margin-right: var(--dimension-3);
}
</style>
