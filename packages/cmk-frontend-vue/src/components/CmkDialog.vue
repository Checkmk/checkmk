<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import type { IconNames } from 'cmk-shared-typing/typescript/icon'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { computed, onMounted, ref, watch } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import { persistWarningDismissal } from '@/lib/rest-api-client/userConfig'
import usePersistentRef from '@/lib/usePersistentRef'
import { isWarningDismissed } from '@/lib/userConfig'

import CmkButton, { type ButtonVariants } from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkSpace from '@/components/CmkSpace.vue'

export interface CmkDialogProps {
  title?: TranslatedString | undefined
  message: TranslatedString
  buttons?: { title: TranslatedString; variant: ButtonVariants['variant']; onclick: () => void }[]
  dismissal_button?: { title: TranslatedString; key: DismissalButtonKey }
  variant?: Variants
  autoDismiss?: number | undefined
}

export type DismissalButtonKey = components['schemas']['UserDismissWarning']['warning']

const props = defineProps<CmkDialogProps>()

const open = defineModel<boolean>('open', { default: true })

let timeoutId: number | null = null

watch(
  open,
  (newOpen) => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    if (newOpen && props.autoDismiss) {
      timeoutId = window.setTimeout(() => {
        open.value = false
      }, props.autoDismiss)
    }
  },
  { immediate: true }
)

const propsCva = cva('', {
  variants: {
    variant: {
      error: 'cmk-dialog__icon-box--error',
      warning: 'cmk-dialog__icon-box--warning',
      success: 'cmk-dialog__icon-box--success',
      info: 'cmk-dialog__icon-box--info'
    }
  },
  defaultVariants: {
    variant: 'info'
  }
})

export type Variants = VariantProps<typeof propsCva>['variant']

const dialogHidden = props.dismissal_button
  ? usePersistentRef(props.dismissal_button.key, false, (v) => v as boolean, 'session')
  : ref(false)

async function hideContent(event?: Event) {
  if (props.dismissal_button) {
    // Stop event propagation to prevent affecting parent components
    event?.stopPropagation()

    dialogHidden.value = true

    await persistWarningDismissal(props.dismissal_button.key)
  }
}

const iconName = computed<IconNames>(() => {
  switch (props.variant) {
    case 'error':
    case 'warning':
      return 'host-svc-problems'
    case 'success':
      return 'check'
    default:
      return 'info'
  }
})

onMounted(() => {
  if (props.dismissal_button) {
    dialogHidden.value = isWarningDismissed(props.dismissal_button.key, dialogHidden.value)
  }
  open.value = !dialogHidden.value
})
</script>

<template>
  <div v-if="open && !dialogHidden" class="cmk-dialog help">
    <div :class="['cmk-dialog__icon-box', propsCva({ variant: props.variant })]">
      <CmkIcon :class="'cmk-dialog__icon'" :name="iconName" :size="'small'" />
    </div>
    <div class="cmk-dialog__content">
      <span v-if="props.title" class="cmk-dialog__title">{{ props.title }}<br /></span>
      <span>{{ props.message }}</span>
      <div v-if="(props.buttons?.length ?? 0) > 0 || props.dismissal_button" class="buttons">
        <CmkSpace :direction="'vertical'" />
        <!-- eslint-disable vue/valid-v-for since no unique identifier is present for key -->
        <template v-for="button in props.buttons">
          <CmkButton :variant="button.variant" @click="button.onclick">
            {{ button.title }}
          </CmkButton>
          <CmkSpace />
        </template>
        <!-- eslint-enable vue/valid-v-for -->
        <CmkButton v-if="props.dismissal_button" @click="hideContent($event)">
          {{ props.dismissal_button.title }}
        </CmkButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
div.cmk-dialog {
  display: flex;

  div.cmk-dialog__content {
    background-color: var(--default-dialog-bg-color);
    color: var(--default-dialog-font-color);
    border-radius: 0 4px 4px 0;
    flex-grow: 1;
    padding: var(--spacing);
    white-space: pre-line;

    & > .cmk-dialog__title {
      font-weight: var(--font-weight-bold);
      margin-bottom: var(--spacing);
      display: block;
    }
  }

  .cmk-dialog__icon-box {
    display: flex;
    align-items: center;
    border-radius: var(--dimension-3) 0 0 var(--dimension-3);
  }

  .cmk-dialog__icon {
    filter: brightness(0) invert(1);
    padding: var(--dimension-4);
  }

  .cmk-dialog__icon-box--info {
    background-color: var(--color-dark-blue-50);
  }

  .cmk-dialog__icon-box--error {
    background-color: var(--color-dark-red-50);
  }

  .cmk-dialog__icon-box--warning {
    background-color: var(--color-warning);

    .cmk-dialog__icon {
      filter: brightness(0);
    }
  }

  .cmk-dialog__icon-box--success {
    background-color: var(--color-corporate-green-50);

    .cmk-dialog__icon {
      filter: none;
    }
  }
}
</style>
