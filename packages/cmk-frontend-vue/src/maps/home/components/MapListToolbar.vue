<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The controls over the map list: how many maps it holds, which of them to show,
a search, and whether they are drawn as cards or as a table. The page title and
the actions that create or import a map are one level up, in ``MapListHeader``.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MapScope, ScopeOption } from '@/maps/home/composables/useMapListFilter'
import MapsViewSwitch, { type ViewSwitchOption } from '@/maps/shared/components/MapsViewSwitch.vue'
import type { MapListView } from '@/maps/types/api'

defineProps<{
  scopeOptions: ScopeOption[]
  showScopeFilter: boolean
  /** How many maps the list below shows, after scope and search. */
  count: number
  /** Whether the list below is drawn as cards or as a table. */
  viewMode: MapListView
  viewModeOptions: ViewSwitchOption<MapListView>[]
}>()

const emit = defineEmits<{ 'update:viewMode': [value: MapListView] }>()

const scope = defineModel<MapScope>('scope', { required: true })
const searchQuery = defineModel<string>('searchQuery', { required: true })

const { _t, _tn } = usei18n()
</script>

<template>
  <div class="maps-map-list-toolbar">
    <!-- A Checkmk listing says how many rows it has; here that number also
         reports what the scope and the search left. -->
    <span class="maps-map-list-toolbar__count">
      {{ _tn('%{n} map', '%{n} maps', count, { n: count }) }}
    </span>
    <div
      v-if="showScopeFilter"
      class="maps-map-list-toolbar__scope"
      role="group"
      :aria-label="_t('Show maps')"
    >
      <CmkChip
        v-for="option in scopeOptions"
        :key="option.value"
        type="button"
        :aria-pressed="option.value === scope"
        :color="option.value === scope ? 'success' : 'others'"
        :variant="option.value === scope ? 'fill' : 'outline'"
        @click="scope = option.value"
      >
        {{ option.label }}
      </CmkChip>
    </div>
    <CmkSearchInput
      v-model="searchQuery"
      class="maps-map-list-toolbar__search"
      :placeholder="_t('Search maps…')"
    />
    <MapsViewSwitch
      :model-value="viewMode"
      :options="viewModeOptions"
      :label="_t('Map list drawing')"
      @update:model-value="emit('update:viewMode', $event)"
    />
  </div>
</template>

<style scoped>
/* The count and the scope filter sit left, the search and the card/table switch
   end flush at the right edge — the list itself uses the full content width. */
.maps-map-list-toolbar {
  display: flex;
  align-items: center;
  gap: var(--dimension-6);
  margin-bottom: var(--dimension-5);
}

.maps-map-list-toolbar__count {
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.maps-map-list-toolbar__scope {
  display: flex;
  gap: var(--dimension-3);
}

.maps-map-list-toolbar__search {
  width: 260px;
  margin-left: auto;
}
</style>
