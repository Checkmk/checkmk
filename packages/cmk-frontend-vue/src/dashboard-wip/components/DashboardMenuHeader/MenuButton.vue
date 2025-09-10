<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import CmkButton from '@/components/CmkButton.vue'

const { variant = 'secondary', disabled = false } = defineProps<{
  variant?: 'primary' | 'secondary'
  disabled?: boolean
}>()

defineEmits<{
  click: [event: MouseEvent]
}>()

const buttonRef = useTemplateRef<InstanceType<typeof CmkButton>>('buttonRef')

defineExpose({
  focus: () => {
    buttonRef.value?.focus()
  }
})
</script>

<template>
  <CmkButton
    ref="buttonRef"
    :variant="variant"
    :disabled="disabled"
    class="cmk-menu-button"
    @click="$emit('click', $event)"
  >
    <slot />
  </CmkButton>
</template>

<style scoped>
.cmk-menu-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--dimension-6) var(--dimension-4);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
}
</style>
