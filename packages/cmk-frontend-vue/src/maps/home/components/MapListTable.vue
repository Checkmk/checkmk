<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list as tables, laid out like Checkmk's other customizable elements
(pagetypes' ``ListPage``, the views and dashboards lists): one table each for
this user's maps, other users' and the built-in ones, every row starting with
its actions and the map's ID. One row per map lives in MapListTableRow.

Shape, density and colour follow Checkmk's own listings (``table.data`` in
``_pages.scss``): a full-width table with no frame of its own, a header on the
zebra's darker tone, and rows at the height a long list can still be scanned at.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import MapListTableRow from '@/maps/home/components/MapListTableRow.vue'
import { isBulkSelectable } from '@/maps/home/composables/useMapBulkActions'
import { type MapSortColumn, useMapListSort } from '@/maps/home/composables/useMapListSort'
import { useShowConnection } from '@/maps/home/composables/useShowConnection'
import { useAuth } from '@/maps/services/context'
import type { MapRead } from '@/maps/types/api'
import { type MapOwnerKind, mapOwnerKind } from '@/maps/utils/mapVisibility'

interface Column {
  id: MapSortColumn
  label: TranslatedString
  numeric?: boolean
  /** The one column that absorbs the width the others do not need. */
  stretch?: boolean
}

interface Group {
  kind: MapOwnerKind
  title: TranslatedString
  maps: MapRead[]
  /** The maps of the group a selection can act on, i.e. delete. */
  selectable: MapRead[]
}

const props = defineProps<{
  maps: readonly MapRead[]
  selectedMaps: Set<string>
}>()

const emit = defineEmits<{
  'toggle-select': [name: string]
  'toggle-select-group': [names: string[], checked: boolean]
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { _t } = usei18n()
const auth = useAuth()

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
  { id: 'id', label: _t('ID') },
  { id: 'name', label: _t('Title'), stretch: true },
  { id: 'type', label: _t('Type') },
  ...(showConnection.value ? [{ id: 'connection' as const, label: _t('Connection') }] : []),
  { id: 'objects', label: _t('Objects'), numeric: true },
  { id: 'owner', label: _t('Owner') },
  { id: 'visibility', label: _t('Visibility') }
])

const { column, direction, sortedMaps, toggleColumn, ariaSort } = useMapListSort(
  () => props.maps,
  () => auth.user.value?.user_id,
  _t
)

const groupTitles = computed<Record<MapOwnerKind, TranslatedString>>(() => ({
  you: _t('Customized'),
  other: _t('Owned by other users'),
  builtin: _t('Built-in')
}))

const groups = computed<Group[]>(() =>
  (['you', 'other', 'builtin'] as const)
    .map((kind) => {
      const maps = sortedMaps.value.filter(
        (map) => mapOwnerKind(map, auth.user.value?.user_id) === kind
      )
      return {
        kind,
        title: groupTitles.value[kind],
        maps,
        selectable: maps.filter(isBulkSelectable)
      }
    })
    .filter((group) => group.maps.length > 0)
)

function allSelected(group: Group): boolean {
  return group.selectable.every((map) => props.selectedMaps.has(map.name))
}
</script>

<template>
  <div class="maps-map-list-table">
    <section
      v-for="group in groups"
      :key="group.kind"
      class="maps-map-list-table__group"
      :aria-label="group.title"
    >
      <h3 class="maps-map-list-table__title">{{ group.title }}</h3>
      <table class="maps-map-list-table__table">
        <thead>
          <tr>
            <th v-if="group.selectable.length > 0" scope="col" class="maps-map-list-table__th">
              <CmkCheckbox
                :model-value="allSelected(group)"
                :aria-label="_t('Select all maps in %{group}', { group: group.title })"
                @update:model-value="
                  emit(
                    'toggle-select-group',
                    group.selectable.map((map) => map.name),
                    $event
                  )
                "
              />
            </th>
            <th v-if="showActions" scope="col" class="maps-map-list-table__th">
              {{ _t('Actions') }}
            </th>
            <th
              v-for="col in columns"
              :key="col.id"
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
          </tr>
        </thead>
        <tbody>
          <MapListTableRow
            v-for="map in group.maps"
            :key="map.name"
            :map="map"
            :selected="selectedMaps.has(map.name)"
            :show-select="group.selectable.length > 0"
            :show-actions="showActions"
            @toggle-select="emit('toggle-select', $event)"
            @clone="emit('clone', $event)"
            @export="emit('export', $event)"
            @delete="emit('delete', $event)"
          />
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.maps-map-list-table {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

/* The bar Checkmk's listings put above each of their tables (``h3.table``). */
.maps-map-list-table__title {
  margin: 0;
  padding: var(--dimension-3) var(--dimension-4);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  background-color: var(--ux-theme-3);
}

/* No frame, no rounding: a Checkmk listing is the page's full width, and the
   zebra alone tells the rows apart. */
.maps-map-list-table__table {
  width: 100%;
  font-size: var(--font-size-normal);
  border-collapse: collapse;
  border-spacing: 0;
}

.maps-map-list-table__th {
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

/* Everything but the title takes the width it needs; the title gets the rest,
   so the facts stay together instead of drifting across the page. */
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
