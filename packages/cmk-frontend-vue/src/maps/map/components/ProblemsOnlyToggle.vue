<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
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
    <CmkIcon name="host-svc-problems" size="small" :colored="modelValue" />
  </button>
</template>

<style scoped>
.maps-problems-only-toggle {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0;
}

.maps-problems-only-toggle:hover {
  background: var(--input-hover-bg-color);
}

.maps-problems-only-toggle:focus-visible {
  outline: revert;
}

.maps-problems-only-toggle--active {
  border-color: var(--color-state-warning);
  background: color-mix(in srgb, var(--color-state-warning) var(--status-tint-mix), transparent);
}
</style>
