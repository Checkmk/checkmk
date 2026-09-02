<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The countdown to the next map in a rotation, and the button that holds it.

A rotating wall is meant to be left alone, but the moment somebody wants to look
at what is on screen they need it to stop — so the countdown itself is the pause
control.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  /** Seconds until the next map. */
  seconds: number
  paused: boolean
}>()

defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    type="button"
    class="maps-map-rotation-pill"
    :class="paused ? 'maps-map-rotation-pill--paused' : ''"
    :title="paused ? _t('Resume rotation') : _t('Pause rotation')"
    @click="$emit('toggle')"
  >
    <svg
      class="maps-map-rotation-pill__icon"
      :class="paused ? '' : 'maps-map-rotation-pill__icon--spinning'"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
      />
    </svg>
    {{ _t('%{seconds}s', { seconds }) }}
  </button>
</template>

<style scoped>
.maps-map-rotation-pill {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-2) 7px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  color: var(--color-state-ok);
  background: color-mix(in srgb, var(--color-state-ok) 8%, transparent);
  border: 0;
  border-radius: 9999px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-state-ok) 20%, transparent);
  cursor: pointer;
}

.maps-map-rotation-pill--paused {
  color: var(--font-color-dimmed);
  background: var(--input-hover-bg-color);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-map-rotation-pill__icon {
  width: 10px;
  height: 10px;
}

.maps-map-rotation-pill__icon--spinning {
  animation: maps-map-rotation-pill__spin 3s linear infinite;
}

@keyframes maps-map-rotation-pill__spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-map-rotation-pill__icon--spinning {
    animation: none;
  }
}
</style>
