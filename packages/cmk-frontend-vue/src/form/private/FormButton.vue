<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkIcon from '@/components/CmkIcon'
import type { SimpleIcons } from '@/components/CmkIcon'

export interface FormButtonProps {
  icon?: SimpleIcons | null
  disabled?: boolean | string | undefined
}
const buttonRef = ref<HTMLButtonElement | null>(null)

// Expose the focus method
defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})

const props = defineProps<FormButtonProps>()
const iconName = props.icon || 'plus'
const isDisabled = computed(() => props.disabled === true || props.disabled === 'true')

defineEmits(['click'])
</script>

<template>
  <button
    ref="buttonRef"
    class="form-button"
    :class="{ 'form-button--disabled': isDisabled }"
    :disabled="isDisabled"
    @click.prevent="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <CmkIcon :name="iconName" variant="inline" size="small" />
    <slot />
  </button>
</template>

<style scoped>
.form-button {
  display: inline-flex;
  height: var(--form-field-height);
  padding: 0 8px;
  margin: 0;
  align-items: center;
  font-weight: var(--font-weight-normal);
  letter-spacing: unset;
  background-color: var(--default-button-form-color);
  border: 1px solid var(--button-form-border-color);
  color: var(--button-form-text-color);

  &:hover:not(.form-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-form-color) 90%, var(--white) 10%);
  }

  &:active:not(.form-button--disabled) {
    background-color: color-mix(
      in srgb,
      var(--default-button-form-color) 90%,
      var(--color-conference-grey-10) 10%
    );
  }
}

button.form-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
