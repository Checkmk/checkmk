<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const props = defineProps<{
  label: string
  active: boolean
}>()

const emit = defineEmits<{
  activate: []
  deactivate: []
}>()

function toggle(): void {
  if (props.active) {
    emit('deactivate')
  } else {
    emit('activate')
  }
}
</script>

<template>
  <button
    type="button"
    class="monitoring-quick-filter-chip"
    :class="{ 'monitoring-quick-filter-chip--active': active }"
    :aria-pressed="active"
    @click="toggle"
  >
    {{ label }}
  </button>
</template>

<style scoped>
.monitoring-quick-filter-chip {
  display: inline-flex;
  align-items: center;
  padding: var(--dimension-2) var(--dimension-4);
  font: inherit;
  font-size: 0.875em;
  line-height: 1;
  color: inherit;
  background: transparent;
  border: 1px solid var(--ux-theme-10);
  border-radius: 9999px;
  cursor: pointer;
  white-space: nowrap;
  transition:
    background-color 0.1s,
    border-color 0.1s,
    color 0.1s;

  &:hover {
    background-color: var(--ux-theme-3);
  }

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }
}

.monitoring-quick-filter-chip--active {
  color: var(--ux-theme-1);
  background-color: var(--font-color, currentcolor);
  border-color: transparent;

  &:hover {
    opacity: 0.85;
    background-color: var(--font-color, currentcolor);
  }
}
</style>
