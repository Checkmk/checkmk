<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  hidden: boolean
  ariaLabel?: string | undefined
}>()

defineEmits<{
  toggle: []
}>()
</script>

<template>
  <button
    type="button"
    class="graphing-graph-legend-eye-button"
    :aria-pressed="!hidden"
    :aria-label="ariaLabel"
    @click="$emit('toggle')"
  >
    <svg
      v-if="hidden"
      class="graphing-graph-legend-eye-button__icon"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <g stroke="currentColor" stroke-opacity="0.7" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 1L11 11" />
        <path
          d="M3.35638 3.3613C1.83239 4.39763 1 6 1 6C1 6 2.81818 9.5 6 9.5C7.02515 9.5 7.9087 9.1367 8.63555 8.6442M5.5 2.52911C5.6627 2.51006 5.8294 2.5 6 2.5C9.1818 2.5 11 6 11 6C11 6 10.6541 6.66585 10 7.41675"
        />
        <path
          d="M7 7.11835C6.7346 7.35585 6.3842 7.5003 6 7.5003C5.17155 7.5003 4.5 6.82875 4.5 6.0003C4.5 5.58845 4.66596 5.2154 4.93466 4.94434"
        />
      </g>
    </svg>
    <svg
      v-else
      class="graphing-graph-legend-eye-button__icon"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M0.5 6C0.5 6 2.5 2 6 2C9.5 2 11.5 6 11.5 6" />
        <path d="M0.5 6C0.5 6 2.5 10 6 10C9.5 10 11.5 6 11.5 6" />
        <path
          d="M6 7.5C6.82843 7.5 7.5 6.82843 7.5 6C7.5 5.17157 6.82843 4.5 6 4.5C5.17157 4.5 4.5 5.17157 4.5 6C4.5 6.82843 5.17157 7.5 6 7.5Z"
        />
      </g>
    </svg>
  </button>
</template>

<style scoped lang="scss">
.graphing-graph-legend-eye-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  border-radius: var(--border-radius);

  &:hover {
    background: rgb(0 0 0 / 8%);
  }
}

.graphing-graph-legend-eye-button__icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
}
</style>
