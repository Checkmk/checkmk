<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogClose, DialogTitle } from 'reka-ui'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon, { type CmkIconProps } from '@/components/CmkIcon'
import CmkSlideIn, { type SlideInVariants } from '@/components/CmkSlideIn'

import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkHeading from './typography/CmkHeading.vue'

const { _t } = usei18n()

const scrollContainerRef = ref<InstanceType<typeof CmkScrollContainer>>()
const scrollContainerEl = computed(() => {
  const el = scrollContainerRef.value?.$el
  return el instanceof HTMLElement ? el : undefined
})

export interface CmkSlideInDialogProps {
  open: boolean
  size?: SlideInVariants['size']
  isIndexPage?: boolean | undefined // will be removed after the removal of the iframe
  stackPriority?: number | undefined
  header?: {
    title: string
    icon?: CmkIconProps | undefined
    closeButton: boolean
  }
  borderColor?: SlideInVariants['borderColor']
  // Controls the title margin and content padding.
  // "wide" gives a roomier layout (e.g. for the Explain-with-AI panel).
  spacing?: 'default' | 'wide'
}
defineProps<CmkSlideInDialogProps>()
const emit = defineEmits(['close'])
</script>

<template>
  <CmkSlideIn
    :aria-label="header?.title"
    :open="open"
    :is-index-page="isIndexPage"
    :size="size"
    :stack-priority="stackPriority"
    :border-color="borderColor"
    :initial-focus-target="scrollContainerEl"
    @close="emit('close')"
  >
    <DialogTitle
      v-if="header"
      class="cmk-slide-in-dialog__title"
      :class="{ 'cmk-slide-in-dialog--spacing-wide': spacing === 'wide' }"
    >
      <CmkHeading type="h1" class="cmk-slide-in-dialog__title-header">
        <CmkIcon v-if="header.icon" v-bind="header.icon" />
        {{ header.title }}
      </CmkHeading>
      <!-- @vue-ignore @click is not a property of DialogClose -->
      <DialogClose
        v-if="header.closeButton"
        class="cmk-slide-in-dialog__close"
        @click="emit('close')"
      >
        <CmkIcon :aria-label="_t('Close')" name="close" size="xsmall" />
      </DialogClose>
    </DialogTitle>

    <CmkScrollContainer
      ref="scrollContainerRef"
      type="outer"
      class="cmk-slide-in-dialog__content"
      :class="{ 'cmk-slide-in-dialog--spacing-wide': spacing === 'wide' }"
      tabindex="0"
      role="region"
      :aria-label="header?.title ?? _t('Content')"
    >
      <slot />
    </CmkScrollContainer>
  </CmkSlideIn>
</template>

<style scoped>
.cmk-slide-in-dialog__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;

  .cmk-slide-in-dialog__title-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--dimension-5);
  }

  label {
    margin-right: 10px;
  }
}

.cmk-slide-in-dialog__title.cmk-slide-in-dialog--spacing-wide {
  margin: var(--dimension-10) var(--dimension-10) var(--dimension-8);
}

.cmk-slide-in-dialog__content {
  --cmk-slide-in-dialog-inset: 20px;

  padding: 0 var(--cmk-slide-in-dialog-inset);
}

.cmk-slide-in-dialog__content.cmk-slide-in-dialog--spacing-wide {
  --cmk-slide-in-dialog-inset: var(--dimension-10);
}

.cmk-slide-in-dialog__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

button {
  margin: 0 10px 0 0;
}
</style>
