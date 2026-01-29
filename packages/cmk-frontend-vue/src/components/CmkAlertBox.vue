<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import CmkHeading from './typography/CmkHeading.vue'

const { _t } = usei18n()

const propsCva = cva('', {
  variants: {
    variant: {
      error: 'cmk-alert-box--error',
      warning: 'cmk-alert-box--warning',
      success: 'cmk-alert-box--success',
      info: 'cmk-alert-box--info',
      loading: 'cmk-alert-box--loading'
    },
    size: {
      small: 'cmk-alert-box--small',
      medium: 'cmk-alert-box--medium'
    }
  },
  defaultVariants: {
    variant: 'info',
    size: 'medium'
  }
})

export type Variants = VariantProps<typeof propsCva>['variant']
export type Sizes = VariantProps<typeof propsCva>['size']

export interface CmkAlertBoxProps {
  variant?: Variants
  size?: Sizes
  heading?: string | undefined
}

const props = defineProps<CmkAlertBoxProps>()

const open = defineModel<boolean>('open', { default: true })

const dismissible = computed(() => {
  switch (props.variant) {
    case 'success':
      return true
    default:
      return false
  }
})

const alertIconName = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    case 'success':
      return 'success'
    default:
      return 'help'
  }
})

const alertIconColor = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'danger'
    case 'warning':
      return 'warning'
    case 'success':
      return 'success'
    default:
      return 'info'
  }
})
</script>

<template>
  <div v-if="open" class="cmk-alert-box" :class="propsCva({ variant, size })">
    <div class="cmk-alert-box__icon">
      <CmkIcon v-if="variant === 'loading'" name="load-graph" size="large" />
      <CmkMultitoneIcon v-else :name="alertIconName" :primary-color="alertIconColor" size="large" />
    </div>
    <div class="cmk-alert-box__text">
      <CmkHeading v-if="$slots.heading || heading" type="h4">
        <slot name="heading">{{ heading }}</slot>
      </CmkHeading>
      <div class="cmk-alert-box__body">
        <slot />
      </div>
    </div>
    <button
      v-if="dismissible"
      class="cmk-alert-box__close"
      type="button"
      :aria-label="_t('Close')"
      @click="open = false"
    >
      <CmkIcon name="close" size="medium" />
    </button>
  </div>
</template>

<style scoped>
/* TODO: try to unify this component with component FormValidation. the styling should be the same
         for all error messages, so the same base component should be used. */
.cmk-alert-box {
  display: flex;
  align-items: center;
  padding: var(--dimension-4) var(--dimension-5);
  border-radius: var(--border-radius);
  margin: 12px 0;
  gap: var(--dimension-5);
}

.cmk-alert-box__icon {
  flex-shrink: 0;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cmk-alert-box__text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: var(--dimension-3);
  max-width: 100%;
  flex: 1;
}

.cmk-alert-box__close {
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cmk-alert-box--error {
  color: var(--font-color);
  background: color-mix(in srgb, var(--color-dark-red-50) 50%, transparent);
}

.cmk-alert-box--warning {
  color: var(--font-color);
  background-color: color-mix(in srgb, var(--color-yellow-50) 25%, transparent);
}

.cmk-alert-box--success {
  color: var(--font-color);
  background: color-mix(in srgb, var(--color-corporate-green-50) 25%, transparent);
}

.cmk-alert-box--info,
.cmk-alert-box--loading {
  color: var(--font-color);
  background-color: color-mix(in srgb, var(--color-dark-blue-50) 25%, transparent);
}

.cmk-alert-box--small {
  padding: var(--dimension-1) var(--dimension-5);

  .cmk-alert-box__icon {
    width: 14px;
  }
}
</style>
