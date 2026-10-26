<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The line right above the map list: the controls that narrow it (the default
slot) and how many maps are left. The layout lives in the page menu.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{
  /** How many maps the list below shows, after scope and search. */
  count: number
}>()

const { _tn } = usei18n()
</script>

<template>
  <div class="maps-map-list-result-bar">
    <slot />
    <!-- A Checkmk listing says how many rows it has; here that number also
         reports what the scope and the search left. -->
    <span class="maps-map-list-result-bar__count">
      {{ _tn('%{n} map', '%{n} maps', count, { n: count }) }}
    </span>
  </div>
</template>

<style scoped>
.maps-map-list-result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-6);
}

.maps-map-list-result-bar__count {
  margin-left: auto;
  color: var(--font-color-dimmed);
  white-space: nowrap;
}
</style>
