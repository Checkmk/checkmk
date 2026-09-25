<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{
  buffer: string
  index: number
  count: number
}>()

const { _t } = usei18n()
</script>

<template>
  <!-- Stays mounted, so the live region announces the changes. -->
  <div
    class="monitoring-type-to-focus-indicator"
    :class="{ 'monitoring-type-to-focus-indicator--active': buffer }"
    role="status"
    aria-live="polite"
  >
    <template v-if="buffer">
      <span class="monitoring-type-to-focus-indicator__buffer">{{ buffer }}</span>
      <span class="monitoring-type-to-focus-indicator__count">
        <template v-if="count > 0">{{ index + 1 }}/{{ count }}</template>
        <template v-else>{{ _t('no match') }}</template>
      </span>
    </template>
  </div>
</template>

<style scoped>
/* Inside the view, so the navigation and sidebar never cover it. */
.monitoring-type-to-focus-indicator {
  position: absolute;
  bottom: var(--dimension-4);
  left: var(--dimension-4);
  z-index: var(--z-index-title-menu);
  display: flex;
  gap: var(--dimension-4);
  align-items: baseline;
  font-size: var(--font-size-small);
  color: var(--font-color);
  pointer-events: none;
}

.monitoring-type-to-focus-indicator--active {
  padding: var(--dimension-1) var(--dimension-4);
  background: var(--default-dialog-bg-color);
  border: var(--border-width-1) solid var(--default-border-color);
  border-radius: var(--border-radius);
}

.monitoring-type-to-focus-indicator__buffer {
  font-family: monospace;
  font-weight: var(--font-weight-bold);
}

.monitoring-type-to-focus-indicator__count {
  color: var(--font-color-dimmed);
}
</style>

<style>
/* Unscoped: the matches live all over the view. Dashed, as the focus ring is solid green. */
[data-type-to-focus-match]:not(:focus) {
  outline: 1px dashed var(--success);
  outline-offset: -1px;
}
</style>
