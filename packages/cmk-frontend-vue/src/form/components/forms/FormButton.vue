<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkIcon from '@/components/CmkIcon.vue'

export interface FormButtonProps {
  icon?: string | null
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

defineEmits(['click'])
</script>

<template>
  <button
    ref="buttonRef"
    class="form-button"
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
}
</style>
