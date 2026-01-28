<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { ref, useId } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkCollapsible from '@/components/CmkCollapsible'
import CmkIcon from '@/components/CmkIcon'

const { _t } = usei18n()

const propsCva = cva('cmk-catalog-panel', {
  variants: {
    variant: {
      default: 'cmk-catalog-panel--default',
      padded: 'cmk-catalog-panel--padded'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})

const {
  title,
  open: initialOpen = true,
  variant = 'default'
} = defineProps<{
  title: TranslatedString
  open?: boolean
  variant?: NonNullable<VariantProps<typeof propsCva>['variant']>
}>()

const open = ref(initialOpen)

const label = _t('Toggle %{ title }', { title })

const id = useId()
</script>

<template>
  <div :class="propsCva({ variant })">
    <button
      class="cmk-catalog-panel__header"
      :class="{ 'cmk-catalog-panel__header--closed': !open }"
      :title="label"
      :aria-label="label"
      :aria-controls="id"
      @click.prevent="open = !open"
    >
      <CmkIcon
        class="cmk-catalog-panel__icon"
        :class="{ 'cmk-catalog-panel__icon--open': open }"
        name="tree-closed"
        size="xxsmall"
      />
      <slot name="header">{{ title }}</slot>
    </button>
    <CmkCollapsible :content-id="id" :open="open">
      <div class="cmk-catalog-panel__content">
        <slot />
      </div>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.cmk-catalog-panel--default,
.cmk-catalog-panel--padded {
  width: 100%;
  padding: 0;
  margin: var(--spacing) 0;
  border-radius: var(--border-radius);
  border-collapse: collapse;
}

.cmk-catalog-panel__header {
  width: 100%;
  background: var(--ux-theme-3);
  padding: 4px 10px 3px 9px;
  margin: 0;
  font-weight: 700;
  letter-spacing: 1px;
  vertical-align: middle;
  text-align: left;
  border-radius: var(--border-radius) var(--border-radius) 0 0;
  border: none;

  /* Reset global style from global css */
  button&:active {
    box-shadow: none;
  }

  &:hover {
    background: var(--ux-theme-5);
  }

  &.cmk-catalog-panel__header--closed {
    border-radius: var(--border-radius);
  }

  .cmk-catalog-panel__icon {
    transition: transform 0.2s ease-in-out;
    margin-right: var(--spacing);

    &.cmk-catalog-panel__icon--open {
      transform: rotate(90deg);
    }
  }
}

.cmk-catalog-panel__content {
  background: var(--ux-theme-2);
  border-radius: 0 0 var(--border-radius) var(--border-radius);
  padding: var(--spacing-half) var(--spacing);
}

.cmk-catalog-panel--padded .cmk-catalog-panel__header {
  min-height: var(--dimension-8);
  padding: var(--dimension-3) 10px 3px var(--dimension-4);
  transition: border-radius 0.2s ease-in-out;

  .cmk-catalog-panel__icon {
    margin-right: var(--spacing-half);
  }
}

.cmk-catalog-panel--padded .cmk-catalog-panel__content {
  padding: var(--dimension-7);
}
</style>
