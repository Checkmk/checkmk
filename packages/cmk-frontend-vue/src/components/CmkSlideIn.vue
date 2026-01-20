<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'radix-vue'
import { nextTick, ref, watch } from 'vue'

// *************************************************************************************************
// Two different variants of SlideIn overlay are required
// * div for index page [CMK-27892 / CMK-26086]
// * DialogOverlay for inner iframe [CMK-28534]
// div: inner iframe html-body will keep `pointer-events: none` forever after closing
// DialogOverlay: the SlideIn blocks the whole page including sidebar and menubar
//
// As DialogContent exists outside our vue app hierarchy, we manually apply our global vue CSS class
// *************************************************************************************************

const slideInVariants = cva('', {
  variants: {
    size: {
      medium: 'cmk-slide-in--size-medium',
      small: 'cmk-slide-in--size-small'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type SlideInVariants = VariantProps<typeof slideInVariants>

export interface CmkSlideInProps {
  open: boolean
  size?: SlideInVariants['size']
  isIndexPage?: boolean | undefined // will be removed after the removal of the iframe
  ariaLabel?: string | undefined
}

const props = defineProps<CmkSlideInProps>()
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
  <DialogRoot :open="open" :modal="!isIndexPage">
    <DialogPortal :to="isIndexPage ? '#content_area' : 'body'">
      <DialogOverlay v-if="!isIndexPage" class="cmk-slide-in__overlay" @click="emit('close')" />
      <div v-else-if="open" class="cmk-slide-in__overlay" @click="emit('close')" />
      <DialogContent
        ref="dialogContentRef"
        class="cmk-vue-app cmk-slide-in__container"
        :class="slideInVariants({ size: size })"
        :aria-describedby="undefined"
        :aria-label="props.ariaLabel"
        @escape-key-down="emit('close')"
        @open-auto-focus.prevent
        @close-auto-focus.prevent
      >
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style v-if="!isIndexPage">
body:has(.cmk-slide-in__container) {
  overflow: hidden;
}
</style>

<style scoped>
.cmk-slide-in__container {
  width: 80%;
  max-width: 1024px;
  display: flex;
  flex-direction: column;
  position: absolute;
  z-index: var(--z-index-modal);
  top: 0;
  right: 0;
  bottom: 0;
  border-left: 4px solid var(--default-border-color-green);
  background: var(--default-bg-color);

  &.cmk-slide-in--size-small {
    max-width: 768px;
  }

  &[data-state='open'] {
    animation: cmk-slide-in__container-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: cmk-slide-in__container-hide 0.2s ease-in-out;
  }
}

/* Cannot use var() here, see https://drafts.csswg.org/css-env-1/ */
@media screen and (width <= 1024px) {
  .cmk-slide-in--size-medium {
    width: 100%;
    max-width: 100%;
  }
}

@media screen and (width <= 768px) {
  .cmk-slide-in--size-small {
    width: 100%;
    max-width: 100%;
  }
}

@keyframes cmk-slide-in__container-show {
  from {
    opacity: 0;
    transform: translate(50%, 0%);
  }

  to {
    opacity: 1;
    transform: translate(0%, 0%);
  }
}

@keyframes cmk-slide-in__container-hide {
  from {
    opacity: 1;
    transform: translate(0%, 0%);
  }

  to {
    opacity: 0;
    transform: translate(50%, 0%);
  }
}

.cmk-slide-in__overlay {
  backdrop-filter: blur(1.5px);
  position: absolute;
  inset: 0;
  animation: cmk-slide-in__overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
  z-index: var(--z-index-modal-overlay-offset);
}

@keyframes cmk-slide-in__overlay-show {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}
</style>
