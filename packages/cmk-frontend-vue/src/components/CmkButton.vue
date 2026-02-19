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
  title?: string | undefined
  href?: string | undefined
  target?: string | undefined
}
</script>

<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed, ref } from 'vue'

const buttonRef = ref<HTMLButtonElement | HTMLAnchorElement | null>(null)

// Expose the focus method
defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})

const props = defineProps<ButtonProps>()

const isDisabled = computed(() => props.disabled === true || props.disabled === 'true')
const isLink = computed(() => props.href !== undefined)

defineEmits(['click'])
</script>

<template>
  <a
    v-if="isLink"
    ref="buttonRef"
    class="cmk-button"
    :class="buttonVariants({ variant: props.variant, disabled: isDisabled })"
    :href="props.href"
    :target="props.target"
    :title="title || ''"
    @click="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <slot />
  </a>
  <button
    v-else
    ref="buttonRef"
    class="cmk-button"
    :class="buttonVariants({ variant: props.variant, disabled: isDisabled })"
    :disabled="isDisabled"
    :title="title || ''"
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
  font-weight: bold;
  text-decoration: none;
  cursor: pointer;
  box-sizing: border-box;
}

.cmk-button--variant-primary,
.cmk-button--variant-success {
  color: var(--button-primary-text-color);
  background-color: var(--default-button-primary-color);
  border: 1px solid var(--button-primary-border-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-primary-color) 70%, var(--white) 30%);
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-primary-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--variant-secondary {
  background-color: var(--default-button-secondary-color);
  border: 1px solid var(--button-secondary-border-color);
  color: var(--button-secondary-text-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-secondary-color) 90%,
      var(--white) 10%
    );
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-secondary-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--variant-optional {
  background-color: var(--default-button-optional-color);
  border: 1px solid var(--button-optional-border-color);
  color: var(--button-optional-text-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-optional-color) 90%,
      var(--white) 10%
    );
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-optional-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--variant-info {
  background-color: var(--default-button-info-color);
  border: 1px solid var(--button-info-border-color);
  color: var(--button-info-text-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-info-color) 90%, var(--white) 10%);
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-info-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--variant-danger {
  background-color: var(--default-button-danger-color);
  border: 1px solid var(--button-danger-border-color);
  color: var(--button-danger-text-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-danger-color) 90%, var(--white) 10%);
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-danger-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--variant-warning {
  background-color: var(--default-button-warning-color);
  border: 1px solid var(--button-warning-border-color);
  color: var(--button-warning-text-color);

  &:hover:not(.cmk-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-warning-color) 70%, var(--white) 30%);
  }

  &:active:not(.cmk-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-warning-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

.cmk-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;

  /* Reset global style from old framework */
  filter: none;
}

.cmk-button--disabled:active {
  /* Reset global style from old framework */
  box-shadow: none;
}
</style>
