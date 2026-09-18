<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva } from 'class-variance-authority'
import type { ButtonVariants } from 'cmk-ui-library/components/CmkButton'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, onUnmounted, watch } from 'vue'

import CmkHeading from './typography/CmkHeading.vue'

const { _t } = usei18n()

const propsCva = cva('', {
  variants: {
    size: {
      small: 'cmk-alert--small',
      medium: 'cmk-alert--medium'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type Variants = 'error' | 'warning' | 'success' | 'info' | 'loading'
export type Sizes = 'small' | 'medium'

export type CmkAlertButton = { title: TranslatedString; onclick: () => void }
export type CmkAlertOptionalButton = CmkAlertButton & { icon?: SimpleIcons }

const DISMISSIBLE_VARIANTS = ['info', 'success'] as const
type DismissibleVariants = (typeof DISMISSIBLE_VARIANTS)[number]

const ALERT_TO_BUTTON_VARIANT = {
  error: 'danger',
  warning: 'warning',
  success: 'success',
  info: 'info',
  loading: 'info'
} as const satisfies Record<NonNullable<Variants>, ButtonVariants['variant']>

type MessageProps = {
  text: TranslatedString
  autoDismiss?: boolean | undefined
}

type SizeProps =
  | {
      size: 'small'
      heading?: never
      mainButton?: never
      optionalButton?: never
    }
  | {
      size?: 'medium'
      heading?: TranslatedString | undefined
      mainButton?: CmkAlertButton
      optionalButton?: CmkAlertOptionalButton
    }

type VariantProps =
  | { variant?: Variants; dismissible?: false }
  | { variant?: DismissibleVariants; dismissible?: boolean }

export type CmkAlertProps = MessageProps & SizeProps & VariantProps

const props = defineProps<CmkAlertProps>()

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

const isSmall = computed(() => props.size === 'small')

const iconSize = computed(() => (isSmall.value ? 'small' : 'large'))

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
    class="cmk-alert"
    :class="propsCva({ size })"
    :style="{ background: `var(--cmk-alert-box-${variant ?? 'info'}-bg-color)` }"
    :role="variant === 'error' || variant === 'warning' ? 'alert' : 'status'"
  >
    <div class="cmk-alert__icon">
      <CmkIcon v-if="variant === 'loading'" name="load-graph" :size="iconSize" />
      <CmkMultitoneIcon
        v-else
        :name="alertIconName"
        :primary-color="alertIconColor"
        :size="iconSize"
      />
    </div>
    <div class="cmk-alert__text">
      <CmkHeading v-if="heading" type="h4">{{ heading }}</CmkHeading>
      <p class="cmk-alert__body" :title="isSmall ? text : undefined">
        {{ text }}
      </p>
      <div v-if="mainButton || optionalButton" class="cmk-alert__actions">
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
      class="cmk-alert__close"
      type="button"
      :aria-label="_t('Close')"
      @click="open = false"
    >
      <CmkIcon name="close" size="small" />
    </button>
  </div>
</template>

<style scoped>
.cmk-alert {
  color: var(--font-color);
  display: flex;
  align-items: flex-start;
  padding: var(--dimension-5);
  border-radius: var(--border-radius);
  margin: 12px 0;
  gap: var(--dimension-4);
}

.cmk-alert__icon {
  flex-shrink: 0;
  width: 20px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.cmk-alert__text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: var(--dimension-2);
  max-width: 100%;
  flex: 1;
  min-width: 0;
}

.cmk-alert__body {
  width: 100%;
  margin: 0;
  white-space: pre-line;
  color: var(--cmk-alert-box-text-color);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.cmk-alert__text :deep(.cmk-heading) {
  width: 100%;
  font-size: var(--font-size-large);
}

.cmk-alert__close {
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cmk-alert__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
  margin-top: calc(var(--dimension-5) - var(--dimension-2));
}

.cmk-alert--small {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  height: 20px;
  box-sizing: border-box;
  padding: var(--dimension-3);
  border-radius: var(--border-radius-half);
  margin: 0;
  gap: var(--dimension-3);

  .cmk-alert__icon {
    width: 12px;
  }

  .cmk-alert__text {
    flex: 0 1 auto;
  }

  .cmk-alert__body {
    font-size: var(--font-size-normal);
    line-height: normal;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cmk-alert__close {
    margin-left: var(--dimension-5);
  }
}
</style>
