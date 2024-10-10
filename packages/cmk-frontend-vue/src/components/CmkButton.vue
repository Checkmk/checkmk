<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { getIconVariable } from '@/lib/utils'

const buttonVariants = cva('', {
  variants: {
    type: {
      primary: 'button__type-primary',
      secondary: 'button__type-secondary',
      tertiary: 'button__type-tertiary'
    },
    variant: {
      submit: 'button__type-primary',
      cancel: 'button__type-secondary'
    }
  },
  defaultVariants: {
    type: 'secondary'
  }
})
export type ButtonVariants = VariantProps<typeof buttonVariants>

interface ButtonProps {
  /** @property {ButtonVariants['variant']} variant - shortcut for often used buttons*/
  variant?: ButtonVariants['variant']
  /** @property {ButtonVariants['type']} type - three different levels of importance */
  type?: ButtonVariants['type']
}

defineProps<ButtonProps>()
</script>

<template>
  <button class="button" :class="buttonVariants({ type, variant })">
    <img v-if="variant === 'submit'" class="icon submit" />
    <img v-if="variant === 'cancel'" class="icon cancel" />
    <slot />
  </button>
</template>

<style scoped>
.button {
  margin: 0;
}
.button + .button {
  margin-left: 10px;
}
.button__type-primary {
  border: 1px solid var(--default-submit-button-border-color);
}
.button__type-tertiary {
  background: none;
  border: none;
  text-decoration: underline var(--success);
  padding: 0;
  margin: 0;
  font-weight: normal;
}
.icon {
  margin-right: 0.8em;
  margin-left: -0.5em;
}
/* TODO: replace with icon component */
.icon.submit {
  content: v-bind('getIconVariable("save")');
}
.icon.cancel {
  content: v-bind('getIconVariable("cancel")');
}
</style>
