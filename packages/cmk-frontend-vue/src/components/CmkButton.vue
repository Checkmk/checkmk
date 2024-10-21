<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import CmkIcon from '@/components/CmkIcon.vue'

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
    <CmkIcon v-if="variant === 'submit'" variant="inline" name="save" />
    <CmkIcon v-if="variant === 'cancel'" variant="inline" name="cancel" />
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
</style>
