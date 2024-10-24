<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const buttonVariants = cva('', {
  variants: {
    variant: {
      primary: 'button--variant-primary',
      secondary: 'button--variant-secondary',
      tertiary: 'button--variant-tertiary',
      transparent: 'button--variant-transparent',
      info: 'button--variant-info'
    },
    size: {
      small: 'button--size-small',
      medium: ''
    }
  },
  defaultVariants: {
    variant: 'secondary',
    size: 'medium'
  }
})
export type ButtonVariants = VariantProps<typeof buttonVariants>

interface ButtonProps {
  /** @property {ButtonVariants['variant']} variant - three different levels of importance */
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  type?: never // This should help finding problems with changes still using type. Can be removed after 2024-12-01
}

defineProps<ButtonProps>()
</script>

<template>
  <button class="button" :class="buttonVariants({ variant, size })">
    <slot />
  </button>
</template>

<style scoped>
.button {
  display: inline-flex;
  height: 30px;
  margin: 0;
  padding: 0 8px;
  align-items: center;
  letter-spacing: unset;
}
.button--variant-primary {
  border: 1px solid var(--default-submit-button-border-color);
}
.button--variant-tertiary {
  text-decoration: underline var(--success);
}
.button--variant-tertiary,
.button--variant-transparent {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font-weight: normal;
}
.button--variant-info {
  background-color: var(--default-help-icon-bg-color);
  color: var(--white);
}
.button--size-small {
  height: 25px;
}
</style>
