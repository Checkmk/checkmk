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
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MapListViewOption } from '@/maps/home/composables/useMapListViewMode'
import type { MapListView } from '@/maps/types/api'

const props = defineProps<{
  /** How many maps the list below shows, after scope and search. */
  count: number
  /** Whether the list below is drawn as cards or as a table. */
  viewMode: MapListView
  viewModeOptions: MapListViewOption[]
}>()

const emit = defineEmits<{ 'update:viewMode': [value: MapListView] }>()

const { _t, _tn } = usei18n()

// The group hands back a plain string; the option it came from carries the type.
function select(value: string): void {
  const picked = props.viewModeOptions.find((option) => option.value === value)
  if (picked) {
    emit('update:viewMode', picked.value)
  }
}
</script>

<template>
  <div class="maps-map-list-result-bar">
    <!-- A Checkmk listing says how many rows it has; here that number also
         reports what the scope and the search left. -->
    <span class="maps-map-list-result-bar__count">
      {{ _tn('%{n} map', '%{n} maps', count, { n: count }) }}
    </span>
    <CmkToggleButtonGroup
      role="group"
      :aria-label="_t('Map list drawing')"
      :model-value="viewMode"
      :options="viewModeOptions"
      size="small"
      spacing="none"
      @update:model-value="select"
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
