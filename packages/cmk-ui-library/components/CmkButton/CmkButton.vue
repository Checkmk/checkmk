<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkIcon from '../CmkIcon/CmkIcon.vue'
import { type ButtonIcon, type ButtonProps, buttonVariants } from './types'

const buttonRef = ref<HTMLButtonElement | HTMLAnchorElement | null>(null)

// Expose the focus method
defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})

const props = defineProps<ButtonProps>()

const isDisabled = computed(
  () => props.disabled === true || props.disabled === 'true' || props.running === true
)
const blockReason = computed(() => (isDisabled.value ? props.disabledReason : undefined))
const titleText = computed(() => blockReason.value ?? props.title ?? '')
const isLink = computed(() => props.href !== undefined)

const leftIcon = computed<ButtonIcon | undefined>(() =>
  props.icon !== undefined && (props.icon.side ?? 'left') === 'left' ? props.icon : undefined
)
const rightIcon = computed<ButtonIcon | undefined>(() =>
  props.icon?.side === 'right' ? props.icon : undefined
)

defineEmits(['click'])
</script>

<template>
  <a
    v-if="isLink"
    ref="buttonRef"
    class="cmk-button"
    :class="[
      buttonVariants({ variant: props.variant, size: props.size, disabled: isDisabled }),
      { 'cmk-button--with-icon': props.icon !== undefined, 'cmk-button--running': props.running }
    ]"
    :href="isDisabled ? undefined : props.href"
    :target="props.target"
    :title="titleText"
    :aria-busy="props.running"
    @click="
      (e) => {
        if (isDisabled) {
          e.preventDefault()
          return
        }
        $emit('click', e)
      }
    "
  >
    <CmkIcon
      v-if="leftIcon"
      :name="leftIcon.name"
      :rotate="leftIcon.rotate"
      :size="leftIcon.size"
    />
    <slot />
    <CmkIcon
      v-if="rightIcon"
      :name="rightIcon.name"
      :rotate="rightIcon.rotate"
      :size="rightIcon.size"
    />
  </a>
  <button
    v-else
    ref="buttonRef"
    class="cmk-button"
    :class="[
      buttonVariants({ variant: props.variant, size: props.size, disabled: isDisabled }),
      { 'cmk-button--with-icon': props.icon !== undefined, 'cmk-button--running': props.running }
    ]"
    :disabled="isDisabled && blockReason === undefined"
    :aria-disabled="isDisabled"
    :aria-busy="props.running"
    :title="titleText"
    @click.prevent="
      (e) => {
        if (isDisabled) {
          return
        }
        $emit('click', e)
      }
    "
  >
    <CmkIcon
      v-if="leftIcon"
      :name="leftIcon.name"
      :rotate="leftIcon.rotate"
      :size="leftIcon.size"
    />
    <slot />
    <CmkIcon
      v-if="rightIcon"
      :name="rightIcon.name"
      :rotate="rightIcon.rotate"
      :size="rightIcon.size"
    />
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

.cmk-button--with-icon {
  gap: var(--dimension-4);
}

.cmk-button--running {
  animation: cmk-button-pulse 1.2s ease-in-out infinite;
}

@keyframes cmk-button-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
}

.cmk-button--size-medium {
  height: var(--dimension-10);
}

.cmk-button--size-small {
  height: var(--dimension-7);
}

.cmk-button--size-icon-only {
  height: var(--dimension-7);
  padding: 0;
  border-radius: var(--dimension-2);
  aspect-ratio: 1;
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

.cmk-button--variant-text {
  background-color: transparent;
  border: 1px solid transparent;
  color: inherit;
  font-weight: var(--font-weight-default);
  text-decoration: underline;

  &:hover:not(.cmk-button--disabled) {
    background-color: var(--ux-theme-5);
    text-decoration: none;
  }

  &:focus-visible:not(.cmk-button--disabled) {
    outline: none;
    border: 1px solid var(--success);
  }
}

.cmk-button--variant-ai {
  position: relative;
  overflow: hidden;
  background-color: var(--default-button-optional-color);
  border: 1px solid var(--button-optional-border-color);
  color: var(--button-optional-text-color);

  &::after {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    transform: translateX(-100%);
    opacity: 0.2;
    background: linear-gradient(
      90deg,
      transparent 0,
      var(--color-purple-80) 20%,
      var(--color-purple-60) 60%,
      transparent
    );
    animation: cmk-button-ai-shimmer 3s infinite;
    pointer-events: none;
    content: '';
  }

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

@keyframes cmk-button-ai-shimmer {
  100% {
    transform: translateX(100%);
  }
}

.cmk-button--disabled,
button.cmk-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;

  /* Reset global style from old framework */
  filter: none;
}

.cmk-button--disabled:active {
  /* Reset global style from old framework */
  box-shadow: none;
}

.cmk-button:focus-visible {
  outline: revert;
}
</style>
