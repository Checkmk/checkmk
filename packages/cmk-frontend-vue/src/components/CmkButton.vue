<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
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
    },
    disabled: {
      true: 'cmk-button--disabled',
      false: ''
    }
  },
  defaultVariants: {
    variant: 'optional',
    disabled: false
  }
})

export type ButtonVariants = VariantProps<typeof buttonVariants>

export interface ButtonProps {
  variant?: ButtonVariants['variant']
  disabled?: boolean | string | undefined
}
</script>

<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed, ref } from 'vue'

const buttonRef = ref<HTMLButtonElement | null>(null)

// Expose the focus method
defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})

const props = defineProps<ButtonProps>()

const isDisabled = computed(() => props.disabled === true || props.disabled === 'true')

defineEmits(['click'])
</script>

<template>
  <button
    ref="buttonRef"
    class="cmk-button"
    :class="buttonVariants({ variant: props.variant, disabled: isDisabled })"
    :disabled="isDisabled"
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
  height: var(--dimension-10);
  margin: 0;
  padding: 0 8px;
  align-items: center;
  justify-content: center;
  letter-spacing: unset;
  border-radius: var(--dimension-3);
}

.cmk-button--variant-primary,
.cmk-button--variant-secondary {
  border: 1px solid var(--default-submit-button-border-color);
}

.cmk-button--variant-primary,
button.cmk-button--variant-success {
  color: var(--black);
  background-color: var(--color-corporate-green-50, #15d1a0);

  &:hover:not(.cmk-button--disabled) {
    background:
      linear-gradient(
        0deg,
        var(--color-white-30, rgb(255 255 255 / 30%)) 0%,
        var(--color-white-30, rgb(255 255 255 / 30%)) 100%
      ),
      var(--color-corporate-green-50, #15d1a0);
  }
}

.cmk-button--variant-warning {
  background-color: var(--color-warning);
}

.cmk-button--variant-danger {
  background-color: var(--color-danger);
  color: var(--white);
}

button.cmk-button--variant-info {
  background-color: var(--default-help-icon-bg-color);
  color: var(--white);

  &:hover:not(.cmk-button--disabled) {
    background-color: var(--default-help-icon-bg-color-hover);
  }
}

button.cmk-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;

  /* Reset global style from old framework */
  filter: none;
}

button.cmk-button--disabled:active {
  /* Reset global style from old framework */
  box-shadow: none;
}
</style>
