<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { TooltipContent, TooltipPortal, useForwardPropsEmits } from 'reka-ui'
import { type HTMLAttributes, computed } from 'vue'

const propsCva = cva('', {
  variants: {
    variant: {
      unstyled: '',
      text: 'cmk-tooltip-content--variant-text',
      content: 'cmk-tooltip-content--variant-content'
    }
  },
  defaultVariants: {
    variant: 'text'
  }
})

export type Variants = VariantProps<typeof propsCva>['variant']

defineOptions({
  inheritAttrs: false
})

type TooltipContentEmits = {
  escapeKeyDown: [event: KeyboardEvent]
  pointerDownOutside: [event: Event]
}

const emits = defineEmits<TooltipContentEmits>()

interface TooltipContentProps {
  asChild?: boolean
  sideOffset?: number
  side?: 'right' | 'left' | 'top' | 'bottom'
  align?: 'center' | 'end' | 'start'
  avoidCollisions?: boolean
  usePortal?: boolean
}

type NoTitleProps = {
  title?: undefined
  titleAside?: undefined
  titleBold?: false
  titleAlign?: undefined
}

type LeftAlignedTitleProps = {
  title: TranslatedString
  titleAside?: TranslatedString | undefined
  titleBold?: boolean
  titleAlign?: 'left'
}

type AlignedTitleProps = {
  title: TranslatedString
  titleAside?: undefined
  titleBold?: boolean
  titleAlign: 'center' | 'right'
}

type TooltipVariantProps =
  | ({
      /**
       * `unstyled` is deprecated: it only remains for the existing usages that draw their own
       * box. Do not add new usages.
       */
      variant: 'unstyled'
    } & NoTitleProps)
  | ({ variant?: 'text' } & NoTitleProps)
  | ({ variant: 'content' } & (NoTitleProps | LeftAlignedTitleProps | AlignedTitleProps))

const {
  asChild = false,
  side = 'top',
  align = 'center',
  sideOffset = 4,
  avoidCollisions = false,
  usePortal = false,
  class: className = '',
  variant,
  title,
  titleAside,
  titleBold,
  titleAlign
} = defineProps<TooltipContentProps & TooltipVariantProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = computed(() => ({ side, align, sideOffset }))

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <TooltipPortal :disabled="!usePortal">
    <TooltipContent
      v-bind="{ ...forwarded, asChild, avoidCollisions }"
      :class="[className, { 'cmk-tooltip-content__layer': variant !== 'unstyled' }]"
    >
      <slot v-if="variant === 'unstyled'" />
      <div v-else class="cmk-tooltip-content" :class="propsCva({ variant })">
        <div v-if="title" class="cmk-tooltip-content__title-bar">
          <span
            class="cmk-tooltip-content__title"
            :class="[
              `cmk-tooltip-content__title--align-${titleAlign ?? 'left'}`,
              { 'cmk-tooltip-content__title--bold': titleBold }
            ]"
            >{{ title }}</span
          >
          <span v-if="titleAside" class="cmk-tooltip-content__title-aside">{{ titleAside }}</span>
        </div>
        <slot />
      </div>
    </TooltipContent>
  </TooltipPortal>
</template>

<style>
.cmk-tooltip-content__layer {
  z-index: var(--z-index-tooltip-offset);
}
</style>

<style scoped>
.cmk-tooltip-content {
  box-sizing: border-box;
  background-color: var(--ux-theme-5);
  border: 1px solid var(--border-color-subtle);
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
}

.cmk-tooltip-content--variant-text {
  display: inline-flex;
  align-items: center;
  height: var(--dimension-8);
  padding: 0 var(--dimension-4);
  white-space: nowrap;
}

.cmk-tooltip-content--variant-content {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-4);
}

.cmk-tooltip-content__title-bar {
  display: flex;
  align-items: baseline;
  gap: var(--dimension-5);
}

.cmk-tooltip-content__title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmk-tooltip-content__title--align-center {
  text-align: center;
}

.cmk-tooltip-content__title--align-right {
  text-align: right;
}

.cmk-tooltip-content__title--bold {
  font-weight: var(--font-weight-bold);
}

.cmk-tooltip-content__title-aside {
  white-space: nowrap;
}
</style>
