<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export interface ButtonProps {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
}

const buttonVariants = cva('', {
  variants: {
    variant: {
      primary: 'cmk-button--variant-primary', // high emphasis
      secondary: 'cmk-button--variant-secondary', // less prominent
      tertiary: 'cmk-button--variant-tertiary', // heightened attention
      transparent: 'cmk-button--variant-transparent', // used only with icons
      minimal: 'cmk-button--variant-minimal', // subtle styling
      info: 'cmk-button--variant-info' // used only within info dialog
    },
    size: {
      small: 'cmk-button--size-small',
      medium: ''
    }
  },
  defaultVariants: {
    variant: 'secondary',
    size: 'medium'
  }
})

export type ButtonVariants = VariantProps<typeof buttonVariants>
</script>

<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { ref } from 'vue'

const buttonRef = ref<HTMLButtonElement | null>(null)

// Expose the focus method
defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})

defineProps<ButtonProps>()
</script>

<template>
  <button ref="buttonRef" class="cmk-button" :class="buttonVariants({ variant, size })">
    <slot />
  </button>
</template>

<style scoped>
.cmk-button {
  display: inline-flex;
  height: 30px;
  margin: 0;
  padding: 0 8px;
  align-items: center;
  justify-content: center;
  letter-spacing: unset;
}

.cmk-button--variant-primary {
  border: 1px solid var(--default-submit-button-border-color);
}

.cmk-button--variant-tertiary {
  text-underline-offset: 2px;
  text-decoration: underline var(--default-button-emphasis-color);
  text-decoration-thickness: 1px;

  &:hover {
    font-weight: 600;
    text-decoration-thickness: 3px;
  }
}

.cmk-button--variant-tertiary,
.cmk-button--variant-transparent,
.cmk-button--variant-minimal {
  height: auto;
  background: none;
  border: none;
  font-weight: normal;
}

.cmk-button--variant-tertiary,
.cmk-button--variant-transparent {
  padding: 0;
  margin: 0;
}

.cmk-button--variant-minimal:hover {
  color: var(--default-button-emphasis-color);
}

.cmk-button--variant-info {
  background-color: var(--default-help-icon-bg-color);
  color: var(--white);

  &:hover {
    background-color: var(--default-help-icon-bg-color-hover);
    color: var(--white);
  }
}

.cmk-button--size-small {
  height: 25px;
}
</style>
