<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map launcher: which maps this user has, as cards or as a table, and the
actions that create, copy, import or remove one.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, ref } from 'vue'

import CreateMapModal from '@/maps/home/components/CreateMapModal.vue'
import MapBulkActionBar from '@/maps/home/components/MapBulkActionBar.vue'
import MapBulkDeleteDialog from '@/maps/home/components/MapBulkDeleteDialog.vue'
import MapBulkEditSlideIn from '@/maps/home/components/MapBulkEditSlideIn.vue'
import MapCardGrid from '@/maps/home/components/MapCardGrid.vue'
import MapCloneDialog from '@/maps/home/components/MapCloneDialog.vue'
import MapListEmptyState from '@/maps/home/components/MapListEmptyState.vue'
import MapListHeader from '@/maps/home/components/MapListHeader.vue'
import MapListTable from '@/maps/home/components/MapListTable.vue'
import MapListToolbar from '@/maps/home/components/MapListToolbar.vue'
import { useMapBulkActions } from '@/maps/home/composables/useMapBulkActions'
import { useMapClone } from '@/maps/home/composables/useMapClone'
import { useMapExport } from '@/maps/home/composables/useMapExport'
import { useMapImport } from '@/maps/home/composables/useMapImport'
import { useMapListFilter } from '@/maps/home/composables/useMapListFilter'
import { useMapListViewMode } from '@/maps/home/composables/useMapListViewMode'
import { useAuth, useConnections, useMaps, useNavigation } from '@/maps/services/context'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import type { MapRead } from '@/maps/types/api'

const { _t } = usei18n()
const auth = useAuth()
const maps = useMaps()
const connections = useConnections()
const nav = useNavigation()

const { searchQuery, scope, scopeOptions, showScopeFilter, displayedMaps, isOrderPristine } =
  useMapListFilter()
const { viewMode, viewModeOptions, setViewMode } = useMapListViewMode()
const { exportMap } = useMapExport()
const clone = useMapClone()
const mapImport = useMapImport()

const showCreate = ref(false)
const confirmDelete = ref<MapRead | null>(null)

const bulk = useMapBulkActions({
  filteredMaps: () => displayedMaps.value,
  viewMode: () => viewMode.value
})

const importInput = ref<HTMLInputElement | null>(null)

const hasMaps = computed(() => maps.maps.value.length > 0)

const deleteMessage = computed(() =>
  confirmDelete.value
    ? _t('Are you sure you want to delete "%{name}"? This action cannot be undone.', {
        name: confirmDelete.value.alias || confirmDelete.value.name
      })
    : untranslated('')
)

const importMessage = computed(() =>
  mapImport.conflict.value
    ? _t('Map "%{name}" already exists. Overwrite?', { name: mapImport.conflict.value.name })
    : untranslated('')
)

async function deleteConfirmed(): Promise<void> {
  const map = confirmDelete.value
  if (!map) {
    return
  }
  confirmDelete.value = null
  await maps.deleteMap(map.name)
}

function openCreatedMap(name: string): void {
  showCreate.value = false
  nav.navigate({ view: 'map', name })
}

onMounted(async () => {
  // The list shows connection display names, which only an administrator sees.
  if (auth.isAdmin.value) {
    void connections.ensureLoaded()
  }
  await maps.fetchMaps()
})
</script>

<template>
  <div class="maps-home-view" role="region" :aria-label="_t('Maps')">
    <main class="maps-home-view__main">
      <MapListHeader @create="showCreate = true" @import="importInput?.click()" />

      <MapListToolbar
        v-if="hasMaps"
        v-model:scope="scope"
        v-model:search-query="searchQuery"
        :scope-options="scopeOptions"
        :show-scope-filter="showScopeFilter"
        :count="displayedMaps.length"
        :view-mode="viewMode"
        :view-mode-options="viewModeOptions"
        @update:view-mode="setViewMode"
      />

      <div v-if="maps.loading.value" class="maps-home-view__loading">
        <CmkLoading />
        {{ _t('Loading…') }}
      </div>

      <CmkAlertBox v-else-if="maps.error.value" variant="error">
        {{ maps.error.value }}
      </CmkAlertBox>

      <MapListEmptyState v-else-if="displayedMaps.length === 0" :search-query="searchQuery" />

      <MapCardGrid
        v-else-if="viewMode === 'cards'"
        :maps="displayedMaps"
        :order-is-pristine="isOrderPristine"
        @clone="clone.start"
        @export="exportMap"
        @delete="confirmDelete = $event"
      />

      <MapListTable
        v-else
        :maps="displayedMaps"
        :selected-maps="bulk.selectedMaps.value"
        :all-selected="bulk.allFilteredSelected.value"
        @toggle-select="bulk.toggleMapSelection"
        @toggle-select-all="bulk.toggleSelectAllFiltered"
        @clone="clone.start"
        @export="exportMap"
        @delete="confirmDelete = $event"
      />
    </main>
  </div>

  <MapsConfirmDialog
    :open="!!confirmDelete"
    variant="error"
    :title="_t('Delete map')"
    :message="deleteMessage"
    :confirm-label="_t('Delete')"
    @confirm="deleteConfirmed"
    @cancel="confirmDelete = null"
  />

  <MapBulkActionBar
    v-if="auth.canCreateMaps.value"
    :count="bulk.selectedCount.value"
    :busy="bulk.bulkBusy.value"
    :select-all-checked="bulk.allFilteredSelected.value"
    :select-all-label="_t('Select all (%{n} visible)', { n: displayedMaps.length })"
    @cancel="bulk.clearSelection"
    @edit="bulk.openBulkEdit"
    @delete="bulk.openBulkDelete"
    @toggle-select-all="bulk.toggleSelectAllFiltered($event)"
  />

  <MapBulkEditSlideIn
    v-if="bulk.showBulkEdit.value"
    :open="bulk.showBulkEdit.value"
    :names="bulk.editableSelectedNames.value"
    :aliases="bulk.editableSelectedAliases.value"
    :saving="bulk.bulkBusy.value"
    @cancel="bulk.showBulkEdit.value = false"
    @apply="bulk.doBulkEdit"
  />

  <MapBulkDeleteDialog
    v-if="bulk.confirmBulkDelete.value"
    :open="bulk.confirmBulkDelete.value"
    :names="bulk.selectedAliases.value"
    :busy="bulk.bulkBusy.value"
    @confirm="bulk.doBulkDelete"
    @cancel="bulk.confirmBulkDelete.value = false"
  />

  <MapCloneDialog
    v-if="clone.source.value"
    :name="clone.name.value"
    :alias="clone.alias.value"
    :error="clone.error.value"
    @update:name="clone.setName"
    @update:alias="clone.alias.value = $event"
    @confirm="clone.clone"
    @cancel="clone.cancel"
  />

  <!-- Opened by the header's "Import" button; a file input has no styling of
       its own worth keeping. -->
  <input
    v-if="auth.canCreateMaps.value"
    ref="importInput"
    type="file"
    accept=".json,.cfg,application/json"
    class="maps-home-view__import-input"
    @change="mapImport.importFile"
  />
  <MapsConfirmDialog
    :open="!!mapImport.conflict.value"
    :title="_t('Import')"
    :message="importMessage"
    :confirm-label="_t('Overwrite')"
    @confirm="mapImport.confirmOverwrite"
    @cancel="mapImport.dismissConflict"
  />

  <CreateMapModal v-if="showCreate" @close="showCreate = false" @created="openCreatedMap" />
</template>

<style scoped>
.maps-home-view {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--ux-theme-1);
}

/* The horizontal padding is the one Checkmk's own page content carries, so the
   toolbar and the list start on the axis of the breadcrumb and the page title
   instead of a step inside it. */
.maps-home-view__main {
  padding: var(--dimension-7) var(--dimension-4) var(--dimension-11);
}

.maps-home-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  padding: var(--dimension-11) 0;
  color: var(--font-color-dimmed);
}

.maps-home-view__import-input {
  display: none;
}
</style>
