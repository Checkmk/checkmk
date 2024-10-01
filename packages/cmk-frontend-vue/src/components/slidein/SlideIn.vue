<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogClose, DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'radix-vue'
import { Label } from '@/quick-setup/components/ui/label'

export interface SlideInProps {
  open: boolean
  header?: {
    title: string
    closeButton: boolean
  }
}

defineProps<SlideInProps>()
const emit = defineEmits(['close'])
</script>

<template>
  <DialogRoot :open="open">
    <DialogPortal>
      <DialogOverlay class="slide-in__overlay" />
      <DialogContent class="slide-in__content" @escape-key-down="emit('close')">
        <div v-if="header" class="slide-in__title">
          <Label variant="title">{{ header.title }}</Label>
          <DialogClose v-if="header.closeButton" class="slide-in__close" @click="emit('close')">
            <div class="slide-in__icon-close" />
          </DialogClose>
        </div>
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.slide-in__content {
  max-width: 80%;
  padding: 20px;
  position: fixed;
  top: 0;
  right: 0;
  height: 100%;
  border-left: 4px solid var(--default-border-color-green);
  background: var(--default-background-color);

  &[data-state='open'] {
    animation: slide-in__content-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: slide-in__content-hide 0.2s ease-in-out;
  }
}

@keyframes slide-in__content-show {
  from {
    opacity: 0;
    transform: translate(50%, 0%);
  }
  to {
    opacity: 1;
    transform: translate(0%, 0%);
  }
}

@keyframes slide-in__content-hide {
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
  margin-bottom: 20px;

  label {
    margin-right: 10px;
  }
}

.slide-in__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

div.slide-in__icon-close {
  width: 10px;
  height: 10px;
  background-size: 10px;
  background-image: var(--icon-close);
}

button {
  margin: 0 10px 0 0;
}
</style>
