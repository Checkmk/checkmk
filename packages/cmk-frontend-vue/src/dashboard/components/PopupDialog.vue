<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'radix-vue'
import { computed, nextTick, ref, useSlots, watch } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { ButtonVariants } from '@/components/CmkButton.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ContentSpacer from './Wizard/components/ContentSpacer.vue'

export interface PopupDialogProps {
  open: boolean
  title?: TranslatedString | undefined
  message: TranslatedString | TranslatedString[]
  variant?: 'info' | 'warning' | 'danger' | 'success' | undefined
  buttons?:
    | { title: TranslatedString; variant: ButtonVariants['variant']; onclick: () => void }[]
    | undefined
  dismissal_button?: { title: TranslatedString; key: string } | undefined
}

const props = defineProps<PopupDialogProps>()
const emit = defineEmits(['close'])
const dialogContentRef = ref<InstanceType<typeof DialogContent>>()

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick(() => {
        dialogContentRef.value?.$el.focus()
      })
    }
  }
)
const messageParagraphs = computed(() =>
  Array.isArray(props.message) ? props.message : [props.message]
)

const slots = useSlots()
</script>

<template>
  <DialogRoot :open="open">
    <DialogPortal>
      <!-- @vue-ignore @click is not a property of DialogOverlay -->
      <DialogOverlay class="db-popup-dialog__overlay" @click="emit('close')" />
      <!-- As this element exists outside our vue app hierarchy, we manually apply our global Vue CSS class -->
      <!-- @vue-ignore aria-describedby it not a property of DialogContent -->
      <DialogContent
        ref="dialogContentRef"
        class="cmk-vue-app db-popup-dialog__container"
        :class="props.variant ? `db-popup-dialog__container-${props.variant.toLowerCase()}` : ''"
        :aria-describedby="undefined"
        @escape-key-down="emit('close')"
        @open-auto-focus.prevent
        @close-auto-focus.prevent
      >
        <CmkHeading class="db-popup-dialog__title">
          <span v-if="props.title">{{ props.title }}</span>
          <CmkIcon
            name="close"
            size="small"
            aria-hidden="true"
            style="float: right; cursor: pointer"
            @click="emit('close')"
          />
        </CmkHeading>

        <ContentSpacer />

        <slot name="preContent" />

        <ContentSpacer v-if="slots?.preContent" />

        <CmkParagraph
          v-for="(paragraph, index) in messageParagraphs"
          :key="index"
          class="db-popup-dialog__body"
        >
          {{ paragraph }}
        </CmkParagraph>

        <ContentSpacer />

        <slot name="postContent" />

        <ContentSpacer v-if="slots?.postContent" />

        <div class="db-popup-dialog__button-bar">
          <div v-for="(button, index) in buttons" :key="index">
            <CmkButton :variant="button.variant" @click="button.onclick">
              {{ button.title }}
            </CmkButton>
            <CmkSpace />
          </div>
          <div>
            <CmkButton v-if="props.dismissal_button" variant="optional" @click="$emit('close')">
              {{ props.dismissal_button.title }}
            </CmkButton>
          </div>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.db-popup-dialog__title {
  color: var(--popup-dialog-title-color);
  font-size: var(--font-size-xlarge);
}

.db-popup-dialog__body {
  color: var(--popup-dialog-message-color);
  font-size: var(--font-size-normal);
}

.db-popup-dialog__button-bar {
  display: flex;
}

.db-popup-dialog__container-success {
  border-top: var(--dimension-3) solid var(--popup-dialog-success);
}

.db-popup-dialog__container-warning {
  border-top: var(--dimension-3) solid var(--popup-dialog-warning);
}

.db-popup-dialog__container-danger {
  border-top: var(--dimension-3) solid var(--popup-dialog-danger);
}

.db-popup-dialog__container-info {
  border-top: var(--dimension-3) solid var(--popup-dialog-info);
}

.db-popup-dialog__container {
  min-width: 450px;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: var(--z-index-modal-popup);
  background: var(--popup-dialog-bg-color);
  padding: var(--dimension-8);

  &[data-state='open'] {
    animation: db-popup-dialog__container-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: db-popup-dialog__container-hide 0.2s ease-in-out;
  }
}

@keyframes db-popup-dialog__container-show {
  from {
    opacity: 0;
    transform: translate(-50%, -48%) scale(0.96);
  }

  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes db-popup-dialog__container-hide {
  from {
    opacity: 1;
  }

  to {
    opacity: 0;
  }
}

.db-popup-dialog__overlay {
  backdrop-filter: blur(1.5px);
  position: fixed;
  inset: 0;
  animation: db-popup-dialog__overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
  background: var(--color-popup-backdrop);
  z-index: var(--z-index-modal-popup-overlay);
}

@keyframes db-popup-dialog__overlay-show {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}
</style>
