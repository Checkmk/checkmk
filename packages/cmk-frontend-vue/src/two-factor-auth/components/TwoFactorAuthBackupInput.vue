<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

type Props = {
  disabled?: boolean
  error?: boolean
}

const { disabled = false, error = false } = defineProps<Props>()

const code = defineModel<string>('modelValue', { default: '' })

const { _t } = usei18n()

const backupInput = ref<HTMLInputElement | null>(null)

defineExpose({
  focus: () => {
    backupInput.value?.focus()
  }
})
</script>

<template>
  <div class="two-factor-auth-backup-input">
    <label class="two-factor-auth-backup-input__label">{{ _t('Backup code:') }}</label>
    <input
      ref="backupInput"
      v-model="code"
      type="text"
      class="two-factor-auth-backup-input__input"
      :class="{ 'two-factor-auth-backup-input__input--error': error }"
      :disabled="disabled"
      :aria-label="_t('Enter backup code')"
    />
  </div>
</template>

<style scoped>
.two-factor-auth-backup-input {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding-top: var(--dimension-5);
  padding-bottom: var(--dimension-8);
}

.two-factor-auth-backup-input__label {
  margin-bottom: 0;
  white-space: nowrap;
}

.two-factor-auth-backup-input__input {
  flex: 1;
  padding: var(--dimension-5);
  font-size: var(--font-size-normal);
  background-color: var(--ux-theme-5);
  border: var(--border-width-1) solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  color: var(--font-color);
  outline: none;
}

.two-factor-auth-backup-input__input:focus {
  border-color: var(--success);
  background-color: var(--ux-theme-5);
}

.two-factor-auth-backup-input__input--error {
  border-color: var(--inline-error-border-color);
}

.two-factor-auth-backup-input__input--error:focus {
  border-color: var(--inline-error-border-color);
  background-color: var(--ux-theme-5);
}

.two-factor-auth-backup-input__input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
