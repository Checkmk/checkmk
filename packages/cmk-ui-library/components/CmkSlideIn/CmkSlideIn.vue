<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { provideFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import { DialogContent, DialogPortal, DialogRoot } from 'reka-ui'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { useSlideInStack } from './useSlideInStack'

// As DialogContent exists outside our vue app hierarchy, we manually apply our global vue CSS class

const slideInVariants = cva('', {
  variants: {
    size: {
      large: 'cmk-slide-in--size-large',
      medium: 'cmk-slide-in--size-medium',
      small: 'cmk-slide-in--size-small'
    },
    borderColor: {
      default: 'cmk-slide-in--border-green',
      purple: 'cmk-slide-in--border-purple'
    }
  },
  defaultVariants: {
    size: 'medium',
    borderColor: 'default'
  }
})

export type SlideInVariants = VariantProps<typeof slideInVariants>

export type Focusable = { focus: () => void }

export interface CmkSlideInProps {
  open: boolean
  size?: SlideInVariants['size']
  ariaLabel?: string | undefined
  stackPriority?: number | undefined
  borderColor?: SlideInVariants['borderColor']
  initialFocusTarget?: Focusable | undefined
}

const props = defineProps<CmkSlideInProps>()
const emit = defineEmits(['close'])
const dialogContentRef = ref<InstanceType<typeof DialogContent>>()

provideFloatingTarget(() => dialogContentRef.value?.$el as HTMLElement | undefined)

const { isTopMost, register, unregister } = useSlideInStack(props.stackPriority ?? null)
const effectiveOpen = computed(() => props.open && isTopMost.value)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      register()
    } else {
      unregister()
    }
  },
  { immediate: true }
)

watch(
  () => effectiveOpen.value,
  async (isOpen) => {
    if (isOpen) {
      await nextTick(() => {
        const target = props.initialFocusTarget ?? dialogContentRef.value?.$el
        if (target && typeof (target as Partial<Focusable>).focus === 'function') {
          ;(target as Focusable).focus()
        }
      })
    }
  }
)

onBeforeUnmount(() => {
  unregister()
})
</script>

<template>
  <DialogRoot v-if="open" :open="effectiveOpen" :modal="false">
    <DialogPortal to="#content_area">
      <div v-if="effectiveOpen" class="cmk-slide-in__overlay" @click="emit('close')" />
      <DialogContent
        ref="dialogContentRef"
        class="cmk-vue-app cmk-slide-in__container"
        :class="slideInVariants({ size: size, borderColor: borderColor })"
        :aria-describedby="undefined"
        :aria-label="props.ariaLabel"
        :force-mount="true"
        @escape-key-down="emit('close')"
        @open-auto-focus.prevent
      >
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

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
  box-sizing: border-box;

  &:focus,
  &:focus-visible {
    outline: none;
    box-shadow: none;
  }

  &.cmk-slide-in--size-small {
    max-width: 768px;
  }

  &.cmk-slide-in--size-large {
    width: calc(100% - var(--dimension-6));
    max-width: calc(100% - var(--dimension-6));
  }

  &.cmk-slide-in--border-green {
    border-left-color: var(--default-border-color-green);
  }

  &.cmk-slide-in--border-purple {
    border-left-color: var(--border-color-purple);
  }

  &[data-state='open'] {
    animation: cmk-slide-in__container-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: cmk-slide-in__container-hide 0.2s ease-in-out;
  }
}

/* Any non-default (non-medium) size needs the container class selector in front to be specific
   enough to override the above width/max-width stylings.
   Cannot use var() here, see https://drafts.csswg.org/css-env-1/ */
@media screen and (width >= 1440px) {
  .cmk-slide-in__container.cmk-slide-in--size-large {
    max-width: calc(1440px - var(--dimension-6));
  }
}

@media screen and (width <= 1024px) {
  .cmk-slide-in--size-medium {
    width: 100%;
    max-width: 100%;
  }
}

@media screen and (width <= 768px) {
  .cmk-slide-in__container.cmk-slide-in--size-small {
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
