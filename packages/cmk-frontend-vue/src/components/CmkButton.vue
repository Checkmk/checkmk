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
      primary: 'button--type-primary',
      secondary: 'button--type-secondary',
      tertiary: 'button--type-tertiary'
    },
    spacing: {
      small: 'button--spacing-small',
      medium: ''
    },
    variant: {
      submit: 'button--type-primary',
      cancel: 'button--type-secondary'
    }
  },
  defaultVariants: {
    type: 'secondary',
    spacing: 'medium'
  }
})
export type ButtonVariants = VariantProps<typeof buttonVariants>

interface ButtonProps {
  /** @property {ButtonVariants['variant']} variant - shortcut for often used buttons*/
  variant?: ButtonVariants['variant']
  /** @property {ButtonVariants['type']} type - three different levels of importance */
  type?: ButtonVariants['type']
  spacing?: ButtonVariants['spacing']
}

defineProps<ButtonProps>()
</script>

<template>
  <button class="button" :class="buttonVariants({ type, variant, spacing })">
    <CmkIcon v-if="variant === 'submit'" variant="inline" name="save" />
    <CmkIcon v-if="variant === 'cancel'" variant="inline" name="cancel" />
    <slot />
  </button>
</template>

<style scoped>
.button {
  margin: 0;
  letter-spacing: unset;
}
.button + .button {
  margin-left: 10px;
}
.button--type-primary {
  border: 1px solid var(--default-submit-button-border-color);
}
.button--type-tertiary {
  background: none;
  border: none;
  text-decoration: underline var(--success);
  padding: 0;
  margin: 0;
  font-weight: normal;
}
.button--spacing-small {
  padding: 5px 8px;
}
</style>
