<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import CmkHeading from './typography/CmkHeading.vue'

const propsCva = cva('', {
  variants: {
    variant: {
      error: 'cmk-alert-box--error',
      warning: 'cmk-alert-box--warning',
      success: 'cmk-alert-box--success',
      info: 'cmk-alert-box--info'
    }
  },
  defaultVariants: {
    variant: 'info'
  }
})

export type Variants = VariantProps<typeof propsCva>['variant']

export interface CmkAlertBoxProps {
  variant?: Variants
  heading?: string | undefined
}

const props = defineProps<CmkAlertBoxProps>()

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
  <div class="cmk-alert-box" :class="propsCva({ variant })">
    <div class="cmk-alert-box__icon">
      <CmkMultitoneIcon :name="alertIconName" :primary-color="alertIconColor" size="large" />
    </div>
    <div class="cmk-alert-box__text">
      <CmkHeading v-if="$slots.heading || heading" type="h4">
        <slot name="heading">{{ heading }}</slot>
      </CmkHeading>
      <div class="cmk-alert-box__body">
        <slot />
      </div>
    </div>
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
}

.cmk-alert-box--error {
  color: var(--font-color);
  background: color-mix(in srgb, var(--color-dark-red-50) 10%, transparent);
}

.cmk-alert-box--warning {
  color: var(--font-color);
  background-color: color-mix(in srgb, var(--color-yellow-50) 10%, transparent);
}

.cmk-alert-box--success {
  color: var(--font-color);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.cmk-alert-box--info {
  color: var(--font-color);
  background-color: color-mix(in srgb, var(--color-dark-blue-50) 10%, transparent);
}
</style>
