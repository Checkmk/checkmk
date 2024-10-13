<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import IconElement from './IconElement.vue'

const buttonVariants = cva('', {
  variants: {
    variant: {
      custom: 'qs-icon-button--custom',
      next: 'qs-icon-button--next',
      prev: 'qs-icon-button--prev',
      save: 'qs-icon-button--save'
    }
  },
  defaultVariants: {
    variant: 'custom'
  }
})
export type ButtonVariants = VariantProps<typeof buttonVariants>

interface IconButtonProps {
  /** @property {string} label - Button's caption */
  label: string

  /** @property {ButtonVariants['variant']} variant - Type of button */
  variant?: ButtonVariants['variant']

  /** @property {string} ariaLabel - Aria label for the button */
  ariaLabel?: string

  /** @property {string} iconName - Name of the icon to be displayed inside the button
      used for custom icon buttons only */
  iconName?: string
}

const props = defineProps<IconButtonProps>()
defineEmits(['click'])

let _iconName = props.iconName || '' // custom and default case
let rotate = 0

if (props?.variant) {
  switch (props.variant) {
    case 'prev':
      _iconName = 'back'
      rotate = 90
      break
    case 'next':
      _iconName = 'continue'
      rotate = 90
      break
    case 'save':
      _iconName = 'save_to_services'
      break
  }
}
</script>

<template>
  <button
    class="qs-icon-button button"
    :class="buttonVariants({ variant })"
    :aria-label="ariaLabel || label"
    @click="$emit('click')"
  >
    <IconElement :name="_iconName" variant="inline" :rotate="rotate" />
    <span>{{ props.label }}</span>
  </button>
</template>

<style scoped>
.qs-icon-button {
  padding: 7px 8px 6px;
  margin: 0 0 0 10px;

  &:first-child {
    margin: 0;
  }

  span {
    position: relative;
    top: 1px;
  }
}

.qs-icon-button--next,
.qs-icon-button--save {
  border: 1px solid var(--default-submit-button-border-color);
}
</style>
