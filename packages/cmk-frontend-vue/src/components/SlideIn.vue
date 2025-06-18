<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import usei18n from '@/lib/i18n'
import {
  DialogClose,
  DialogTitle,
  DialogContent,
  DialogOverlay,
  DialogPortal,
  DialogRoot
} from 'radix-vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkScrollContainer from './CmkScrollContainer.vue'

const { t } = usei18n('cmk-slide-in')

export interface SlideInProps {
  open: boolean
  header?: {
    title: string
    closeButton: boolean
  }
}

const props = defineProps<SlideInProps>()
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
</script>

<template>
  <DialogRoot :open="open">
    <DialogPortal>
      <DialogOverlay class="slide-in__overlay" />
      <!-- As this element exists outside our vue app hierarchy, we manually apply our global Vue CSS class -->
      <DialogContent
        ref="dialogContentRef"
        class="cmk-vue-app slide-in__container"
        :aria-describedby="undefined"
        @escape-key-down="emit('close')"
        @open-auto-focus.prevent
        @close-auto-focus.prevent
      >
        <DialogTitle v-if="header" class="slide-in__title">
          <CmkLabel variant="title">{{ header.title }}</CmkLabel>
          <DialogClose v-if="header.closeButton" class="slide-in__close" @click="emit('close')">
            <CmkIcon :aria-label="t('close-slidein', 'Close')" name="close" size="xsmall" />
          </DialogClose>
        </DialogTitle>

        <CmkScrollContainer type="outer" class="slide-in__content">
          <slot />
        </CmkScrollContainer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.slide-in__container {
  width: 80%;
  max-width: 1024px;
  display: flex;
  flex-direction: column;
  position: fixed;
  z-index: 10;
  top: 0;
  right: 0;
  bottom: 0;
  border-left: 4px solid var(--default-border-color-green);
  background: var(--default-bg-color);

  &[data-state='open'] {
    animation: slide-in__container-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: slide-in__container-hide 0.2s ease-in-out;
  }
}

/* Cannot use var() here, see https://drafts.csswg.org/css-env-1/ */
@media screen and (max-width: 1024px) {
  .slide-in__container {
    width: 100%;
    max-width: 100%;
  }
}

@keyframes slide-in__container-show {
  from {
    opacity: 0;
    transform: translate(50%, 0%);
  }
  to {
    opacity: 1;
    transform: translate(0%, 0%);
  }
}

@keyframes slide-in__container-hide {
  from {
    opacity: 1;
    transform: translate(0%, 0%);
  }
  to {
    opacity: 0;
    transform: translate(50%, 0%);
  }
}

.slide-in__overlay {
  backdrop-filter: blur(1.5px);
  position: fixed;
  inset: 0;
  animation: slide-in__overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-in__overlay-show {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.slide-in__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;

  label {
    margin-right: 10px;
  }
}

.slide-in__content {
  padding: 0 20px;
}

.slide-in__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

button {
  margin: 0 10px 0 0;
}
</style>
