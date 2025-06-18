<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export interface ButtonProps {
  variant?: ButtonVariants['variant']
}

const buttonVariants = cva('', {
  variants: {
    variant: {
      primary: 'cmk-button--variant-primary', // high emphasis (colored background)
      secondary: 'cmk-button--variant-secondary', // low emphasis (colored border)
      optional: 'cmk-button--variant-optional', // default
      success: 'cmk-button--variant-success',
      warning: 'cmk-button--variant-warning',
      danger: 'cmk-button--variant-danger',
      info: 'cmk-button--variant-info' // used only within info dialog
    }
  },
  defaultVariants: {
    variant: 'optional'
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

defineEmits(['click'])
</script>

<template>
  <button
    ref="buttonRef"
    class="cmk-button"
    :class="buttonVariants({ variant })"
    @click.prevent="
      (e) => {
        $emit('click', e)
      }
    "
  >
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

.cmk-button--variant-primary,
.cmk-button--variant-success {
  background-color: var(--success-dimmed);
}

.cmk-button--variant-primary,
.cmk-button--variant-secondary {
  border: 1px solid var(--default-submit-button-border-color);
}

.cmk-button--variant-warning {
  background-color: var(--color-warning);
}

.cmk-button--variant-danger {
  background-color: var(--color-danger);
  color: var(--white);
}

.cmk-button--variant-info {
  background-color: var(--default-help-icon-bg-color);
  color: var(--white);

  &:hover {
    background-color: var(--default-help-icon-bg-color-hover);
  }
}
</style>
