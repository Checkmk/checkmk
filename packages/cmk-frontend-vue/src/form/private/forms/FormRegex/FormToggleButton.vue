<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import type { RegexMode } from './RegexInput.vue'

const { _t } = usei18n()

const mode = defineModel<RegexMode>({ required: true })

const toggleOptions: { label: string; value: RegexMode }[] = [
  { label: _t('Regex'), value: 'regex' },
  { label: _t('Text'), value: 'text' }
]
</script>

<template>
  <div class="form-toggle-button">
    <button
      v-for="option in toggleOptions"
      :key="option.value"
      :class="{ 'form-toggle-button--active': mode === option.value }"
      :aria-pressed="mode === option.value"
      @click.prevent="mode = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.form-toggle-button {
  display: inline-flex;
  align-items: center;
  background-color: var(--ux-theme-0);
  border: 1px solid var(--default-form-element-border-color);
  gap: 2px;
  padding: 0 3px;
  border-top-left-radius: var(--border-radius);
  border-bottom-left-radius: var(--border-radius);
  height: 20px;
  z-index: +1;
}

.form-toggle-button button {
  border: none;
  color: var(--font-color);
  background-color: var(--ux-theme-0);
  font-weight: var(--font-weight-default);
  transition: all 0.2s ease-in-out;
  border-radius: var(--border-radius);
  padding: 1px 3px;
  margin: 0;
  font-size: var(--font-size-normal);
  height: 16px;
}

.form-toggle-button .form-toggle-button--active {
  background-color: var(--interactive-selected);
  color: var(--font-color-on-light);
}
</style>
