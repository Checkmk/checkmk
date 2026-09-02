<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

const props = defineProps<{
  modelValue: boolean
  title?: TranslatedString
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const { _t } = usei18n()
</script>

<template>
  <button
    type="button"
    class="maps-problems-only-toggle"
    :class="{ 'maps-problems-only-toggle--active': modelValue }"
    :title="props.title ?? _t('Show only problems')"
    :aria-pressed="modelValue"
    @click="emit('update:modelValue', !modelValue)"
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12 9v4m0 4h.01M10.29 3.86l-8.48 14.7A1.5 1.5 0 003.1 21h17.8a1.5 1.5 0 001.29-2.44l-8.48-14.7a1.5 1.5 0 00-2.42 0z"
      />
    </svg>
  </button>
</template>

<style scoped>
.maps-problems-only-toggle {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: transparent;
  color: var(--font-color-dimmed);
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0;
}

.maps-problems-only-toggle svg {
  width: 14px;
  height: 14px;
}

.maps-problems-only-toggle:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-problems-only-toggle--active {
  color: var(--color-yellow-50, #fbbf24);
  border-color: var(--color-yellow-50, #fbbf24);
  background: rgb(251 191 36 / 12%);
}
</style>
