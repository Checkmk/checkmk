<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { computed, onMounted, ref, watch } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import { persistWarningDismissal } from '@/lib/rest-api-client/userConfig'
import usePersistentRef from '@/lib/usePersistentRef'
import { isWarningDismissed } from '@/lib/userConfig'

import CmkButton, { type ButtonVariants } from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
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
      info: 'cmk-dialog__icon-box--info',
      loading: 'cmk-dialog__icon-box--loading'
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

const alertIconName = computed(() => {
  switch (props.variant) {
    case 'success':
      return 'checkmark'
    case 'error':
    case 'warning':
      return props.variant
    default:
      return 'info'
  }
})

const alertIconColor = computed(() => {
  switch (props.variant) {
    case 'warning':
    case 'success':
      return { custom: 'black' }
    default:
      return { custom: 'white' }
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
      <CmkIcon v-if="variant === 'loading'" name="load-graph" class="cmk-dialog__icon" />
      <CmkMultitoneIcon
        v-else
        :name="alertIconName"
        :primary-color="alertIconColor"
        class="cmk-dialog__icon"
      />
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
    border: 1px solid transparent;
  }

  .cmk-dialog__icon {
    padding: var(--dimension-2);
  }

  .cmk-dialog__icon-box--info {
    background-color: var(--color-dark-blue-50);
  }

  .cmk-dialog__icon-box--error {
    background-color: var(--color-dark-red-50);
  }

  .cmk-dialog__icon-box--warning {
    background-color: var(--color-warning);
  }

  .cmk-dialog__icon-box--success {
    background-color: var(--color-corporate-green-50);
  }

  .cmk-dialog__icon-box--loading {
    background-color: var(--color-corporate-green-100);
  }
}

body[data-theme='modern-dark'] {
  div.cmk-dialog {
    .cmk-dialog__icon-box--loading {
      border-color: var(--color-corporate-green-70);
    }
  }
}
</style>
