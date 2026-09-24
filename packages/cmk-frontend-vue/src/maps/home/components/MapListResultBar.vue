<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The line right above the map list: how many maps it shows, and whether they are
drawn as cards or as a table. Both are about the list, so they sit on it rather
than in the page header's bar with the search and the page's actions.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import MapsViewSwitch, { type ViewSwitchOption } from '@/maps/shared/components/MapsViewSwitch.vue'
import type { MapListView } from '@/maps/types/api'

defineProps<{
  /** How many maps the list below shows, after scope and search. */
  count: number
  /** Whether the list below is drawn as cards or as a table. */
  viewMode: MapListView
  viewModeOptions: ViewSwitchOption<MapListView>[]
}>()

const emit = defineEmits<{ 'update:viewMode': [value: MapListView] }>()

const { _t, _tn } = usei18n()
</script>

<template>
  <div class="maps-map-list-result-bar">
    <!-- A Checkmk listing says how many rows it has; here that number also
         reports what the scope and the search left. -->
    <span class="maps-map-list-result-bar__count">
      {{ _tn('%{n} map', '%{n} maps', count, { n: count }) }}
    </span>
    <MapsViewSwitch
      :model-value="viewMode"
      :options="viewModeOptions"
      :label="_t('Map list drawing')"
      @update:model-value="emit('update:viewMode', $event)"
    />
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
  color: var(--font-color-dimmed);
  white-space: nowrap;
}
</style>
