<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Why a map is not behaving the way the operator expects: it is somebody else's to
edit, or they are in edit mode and their clicks are selecting rather than
drilling down.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  readonly?: boolean
  editing?: boolean
}>()
</script>

<template>
  <span v-if="readonly" class="maps-map-mode-badges__badge maps-map-mode-badges__badge--readonly">
    <svg
      class="maps-map-mode-badges__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
      />
    </svg>
    {{ _t('Read-only') }}
  </span>
  <span v-if="editing" class="maps-map-mode-badges__badge maps-map-mode-badges__badge--editing">
    <svg
      class="maps-map-mode-badges__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
      />
    </svg>
    {{ _t('Editing') }}
  </span>
</template>

<style scoped>
.maps-map-mode-badges__badge {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  border-radius: 8px;
}

.maps-map-mode-badges__badge--readonly {
  color: var(--font-color-dimmed);
  background: var(--input-hover-bg-color);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-map-mode-badges__badge--editing {
  color: var(--color-state-warning);
  background: color-mix(in srgb, var(--color-state-warning) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-state-warning) 30%, transparent);
}

.maps-map-mode-badges__icon {
  width: 10px;
  height: 10px;
}
</style>
