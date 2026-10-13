<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The controls that narrow the map list: a search and which of the maps to show.
``MapListHeader`` places them in its bar, ahead of the page's own actions; how
many maps are left and how they are drawn is ``MapListResultBar``'s, above the
list itself.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MapScope, ScopeOption } from '@/maps/home/composables/useMapListFilter'

defineProps<{
  scopeOptions: ScopeOption[]
  showScopeFilter: boolean
}>()

const scope = defineModel<MapScope>('scope', { required: true })
const searchQuery = defineModel<string>('searchQuery', { required: true })

const { _t } = usei18n()
</script>

<template>
  <div class="maps-map-list-toolbar">
    <CmkSearchInput
      v-model="searchQuery"
      class="maps-map-list-toolbar__search"
      :placeholder="_t('Search maps…')"
      :show-submit-button="false"
    />
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
  </div>
</template>

<style scoped>
/* Laid out like the global settings search and filter: the scope chips wrap
   below the search once the bar runs out of width. */
.maps-map-list-toolbar {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4) var(--dimension-6);
}

.maps-map-list-toolbar__search {
  flex: 1 1 320px;
  max-width: 400px;
}

.maps-map-list-toolbar__scope {
  display: flex;
  gap: var(--dimension-3);
}
</style>
