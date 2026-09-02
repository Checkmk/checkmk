<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list as a table: the columns this user gets, sorted by the column they
picked. One row per map lives in MapListTableRow.

Shape, density and colour follow Checkmk's own listings (``table.data`` in
``_pages.scss``, and the monitoring views' table): a full-width table with no
frame of its own, a sticky header on the zebra's darker tone, and rows at the
height a long list can still be scanned at.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import MapListTableRow from '@/maps/home/components/MapListTableRow.vue'
import { type MapSortColumn, useMapListSort } from '@/maps/home/composables/useMapListSort'
import { useShowConnection } from '@/maps/home/composables/useShowConnection'
import { useAuth } from '@/maps/services/context'
import type { MapRead } from '@/maps/types/api'

interface Column {
  id: MapSortColumn
  label: TranslatedString
  numeric?: boolean
  /** The one column that absorbs the width the others do not need. */
  stretch?: boolean
}

const props = defineProps<{
  maps: readonly MapRead[]
  selectedMaps: Set<string>
  allSelected: boolean
}>()

const emit = defineEmits<{
  'toggle-select': [name: string]
  'toggle-select-all': [checked: boolean]
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { _t } = usei18n()
const auth = useAuth()

// Checkboxes only make sense for someone who can act on a selection.
const showSelect = computed(() => auth.canCreateMaps.value)
const showConnection = useShowConnection()
/**
 * A non-admin may still hold edit or delete rights on individual maps, and may
 * be able to clone or export any map they see — so the column appears whenever
 * some action is available on some listed map.
 */
const showActions = computed(
  () =>
    auth.canCreateMaps.value ||
    props.maps.some((map) => map.can_edit === true || map.can_delete === true)
)

const columns = computed<Column[]>(() => [
  { id: 'name', label: _t('Name'), stretch: true },
  { id: 'type', label: _t('Type') },
  { id: 'owner', label: _t('Owner') },
  { id: 'visibility', label: _t('Visibility') },
  ...(showConnection.value ? [{ id: 'connection' as const, label: _t('Connection') }] : []),
  { id: 'objects', label: _t('Objects'), numeric: true }
])

const { column, direction, sortedMaps, toggleColumn, ariaSort } = useMapListSort(
  () => props.maps,
  () => auth.user.value?.user_id,
  _t
)
</script>

<template>
  <div class="maps-map-list-table">
    <table class="maps-map-list-table__table">
      <thead>
        <tr>
          <th v-if="showSelect" scope="col" class="maps-map-list-table__th">
            <CmkCheckbox
              :model-value="allSelected"
              :aria-label="_t('Select all visible maps')"
              @update:model-value="emit('toggle-select-all', $event)"
            />
          </th>
          <!-- The actions follow the name, where Checkmk's own Customize
               listings put them (see pagetypes' _show_table). -->
          <template v-for="(col, index) in columns" :key="col.id">
            <th
              scope="col"
              class="maps-map-list-table__th"
              :class="{
                'maps-map-list-table__th--numeric': col.numeric,
                'maps-map-list-table__th--stretch': col.stretch
              }"
              :aria-sort="ariaSort(col.id)"
            >
              <!-- A real button, so sorting is keyboard-operable. The two
                   chevrons ahead of the label are how every sortable Checkmk
                   table shows its direction (see MonitoringTableHeader). -->
              <button type="button" class="maps-map-list-table__sort" @click="toggleColumn(col.id)">
                <span class="maps-map-list-table__sort-marker">
                  <CmkMultitoneIcon
                    name="chevron-up"
                    class="maps-map-list-table__chevron"
                    :class="{
                      'maps-map-list-table__chevron--active':
                        column === col.id && direction === 'asc'
                    }"
                    primary-color="font"
                    size="xsmall"
                    aria-hidden="true"
                  />
                  <CmkMultitoneIcon
                    name="chevron-down"
                    class="maps-map-list-table__chevron"
                    :class="{
                      'maps-map-list-table__chevron--active':
                        column === col.id && direction === 'desc'
                    }"
                    primary-color="font"
                    size="xsmall"
                    aria-hidden="true"
                  />
                </span>
                {{ col.label }}
              </button>
            </th>
            <th v-if="showActions && index === 0" scope="col" class="maps-map-list-table__th">
              {{ _t('Actions') }}
            </th>
          </template>
        </tr>
      </thead>
      <tbody class="maps-map-list-table__body">
        <MapListTableRow
          v-for="map in sortedMaps"
          :key="map.name"
          :map="map"
          :selected="selectedMaps.has(map.name)"
          :show-actions="showActions"
          @toggle-select="emit('toggle-select', $event)"
          @clone="emit('clone', $event)"
          @export="emit('export', $event)"
          @delete="emit('delete', $event)"
        />
      </tbody>
    </table>
  </div>
</template>

<style scoped>
/* No frame, no rounding: a Checkmk listing is the page's full width, and the
   zebra alone tells the rows apart. */
.maps-map-list-table__table {
  width: 100%;
  font-size: var(--font-size-normal);
  border-collapse: collapse;
  border-spacing: 0;
}

.maps-map-list-table__th {
  position: sticky;
  top: 0;
  z-index: 1;
  height: 24px;
  padding: 0 var(--dimension-4);
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
  background-color: var(--odd-tr-bg-color);
  user-select: none;
}

/* Everything but the name takes the width it needs; the name gets the rest, so
   the facts stay together instead of drifting across the page. */
.maps-map-list-table__th--stretch {
  width: 100%;
}

.maps-map-list-table__th--numeric {
  text-align: right;
}

.maps-map-list-table__sort {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  margin: 0;
  padding: 0;
  font: inherit;
  color: inherit;
  background: none;
  border: 0;
  cursor: pointer;
}

.maps-map-list-table__sort:hover {
  color: var(--font-color);
}

.maps-map-list-table__sort:focus-visible {
  outline: revert;
}

/* A right-aligned column reads from its right edge, so its marker goes there. */
.maps-map-list-table__th--numeric .maps-map-list-table__sort {
  flex-direction: row-reverse;
}

.maps-map-list-table__sort-marker {
  display: inline-flex;
  flex-direction: column;
  flex-shrink: 0;
}

.maps-map-list-table__chevron {
  opacity: 0.4;
}

.maps-map-list-table__chevron:last-child {
  margin-top: calc(-1 * var(--dimension-3));
}

.maps-map-list-table__chevron--active {
  opacity: 1;
}
</style>
