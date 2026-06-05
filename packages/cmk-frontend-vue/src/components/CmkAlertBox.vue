<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed, onUnmounted, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { ButtonVariants } from '@/components/CmkButton'
import CmkButton from '@/components/CmkButton'
import CmkIcon from '@/components/CmkIcon'
import type { SimpleIcons } from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import CmkHeading from './typography/CmkHeading.vue'

const { _t } = usei18n()

const propsCva = cva('', {
  variants: {
    size: {
      small: 'cmk-alert-box--small',
      medium: 'cmk-alert-box--medium'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type Variants = 'error' | 'warning' | 'success' | 'info' | 'loading'
export type Sizes = VariantProps<typeof propsCva>['size']

const DISMISSIBLE_VARIANTS = ['info', 'success'] as const
type DismissibleVariants = (typeof DISMISSIBLE_VARIANTS)[number]

const ALERT_TO_BUTTON_VARIANT = {
  error: 'danger',
  warning: 'warning',
  success: 'success',
  info: 'info',
  loading: 'info'
} as const satisfies Record<NonNullable<Variants>, ButtonVariants['variant']>

type BaseProps = {
  size?: Sizes
  heading?: string | undefined
  autoDismiss?: boolean | undefined
  mainButton?: { title: TranslatedString; onclick: () => void }
  optionalButton?: { title: TranslatedString; icon?: SimpleIcons; onclick: () => void }
}

export type CmkAlertBoxProps = BaseProps &
  (
    | { variant?: DismissibleVariants; dismissible?: boolean }
    | { variant: 'error' | 'warning'; dismissible?: false }
    | { variant: 'loading'; dismissible?: false; mainButton?: never; optionalButton?: never }
  )

const props = defineProps<CmkAlertBoxProps>()

const open = defineModel<boolean>('open', { default: true })

let timeoutId: number | null = null

watch(
  [open, () => props.autoDismiss],
  ([newOpen]) => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    if (newOpen && props.autoDismiss) {
      timeoutId = window.setTimeout(() => {
        open.value = false
      }, 6000)
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (timeoutId !== null) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
})

const mainButtonVariant = computed(() => ALERT_TO_BUTTON_VARIANT[props.variant ?? 'info'])

const showCloseButton = computed(
  () =>
    !!props.dismissible &&
    !props.mainButton &&
    !props.optionalButton &&
    DISMISSIBLE_VARIANTS.includes(props.variant ?? 'info')
)

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
  const variant = props.variant && props.variant !== 'loading' ? props.variant : 'info'
  return { custom: `var(--cmk-alert-box-${variant}-icon-color)` }
})
</script>

<template>
  <div
    v-if="open"
    class="cmk-alert-box"
    :class="propsCva({ size })"
    :style="{ background: `var(--cmk-alert-box-${variant ?? 'info'}-bg-color)` }"
    :role="variant === 'error' || variant === 'warning' ? 'alert' : 'status'"
  >
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
      <div v-if="mainButton || optionalButton" class="cmk-alert-box__actions">
        <CmkButton v-if="mainButton" :variant="mainButtonVariant" @click="mainButton.onclick">
          {{ mainButton.title }}
        </CmkButton>
        <CmkButton v-if="optionalButton" variant="optional" @click="optionalButton.onclick">
          <CmkIcon v-if="optionalButton.icon" :name="optionalButton.icon" variant="inline" />
          {{ optionalButton.title }}
        </CmkButton>
      </div>
    </div>
    <button
      v-if="showCloseButton"
      class="cmk-alert-box__close"
      type="button"
      :aria-label="_t('Close')"
      @click="open = false"
    >
      <CmkIcon name="close" size="small" />
    </button>
  </div>
</template>

<style scoped>
/* TODO: try to unify this component with component FormValidation. the styling should be the same
         for all error messages, so the same base component should be used. */
.cmk-alert-box {
  color: var(--font-color);
  display: flex;
  align-items: flex-start;
  padding: var(--dimension-5);
  border-radius: var(--border-radius);
  margin: 12px 0;
  gap: var(--dimension-4);
}

.cmk-alert-box__icon {
  flex-shrink: 0;
  width: 20px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.cmk-alert-box__text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: var(--dimension-2);
  max-width: 100%;
  flex: 1;
  min-width: 0;
}

.cmk-alert-box__body {
  width: 100%;
  white-space: pre-line;
  color: var(--cmk-alert-box-text-color);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.cmk-alert-box__text :deep(.cmk-heading) {
  width: 100%;
  font-size: var(--font-size-large);
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

.cmk-alert-box--small {
  padding: var(--dimension-1) var(--dimension-5);

  .cmk-alert-box__icon {
    width: 14px;
  }
}

.cmk-alert-box__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
  margin-top: calc(var(--dimension-5) - var(--dimension-2));
}
</style>
