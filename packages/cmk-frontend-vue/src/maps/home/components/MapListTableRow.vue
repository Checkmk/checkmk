<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One map as a table row. Which cells it has follows the table's column set, so
the header and the rows stay in step.

The facts are plain text: in Checkmk a colour carries a state, and a map's type
or who may see it is not one.
-->
<script setup lang="ts">
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapConnectionLabel from '@/maps/home/components/MapConnectionLabel.vue'
import MapFlags from '@/maps/home/components/MapFlags.vue'
import MapRowActions from '@/maps/home/components/MapRowActions.vue'
import { useShowConnection } from '@/maps/home/composables/useShowConnection'
import {
  hasDynamicContent,
  mapOwnerLabel,
  mapTypeLabel,
  mapVisibilityLabel
} from '@/maps/home/mapLabels'
import { useAuth } from '@/maps/services/context'
import MapsLink from '@/maps/shared/components/MapsLink.vue'
import type { MapRead } from '@/maps/types/api'

const props = defineProps<{
  map: MapRead
  selected: boolean
  showActions: boolean
}>()

const emit = defineEmits<{
  'toggle-select': [name: string]
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { _t } = usei18n()
const auth = useAuth()

const title = computed(() => props.map.alias || props.map.name)
// A selection is only offered to someone who can act on it. The connection asks
// the same composable the header does, so cells and header cannot disagree.
const showSelect = computed(() => auth.canCreateMaps.value)
const showConnection = useShowConnection()
</script>

<template>
  <tr class="maps-map-list-table-row" :class="{ 'maps-map-list-table-row--selected': selected }">
    <td v-if="showSelect" class="maps-map-list-table-row__select" @click.stop>
      <CmkCheckbox
        :model-value="selected"
        :aria-label="_t('Select %{name}', { name: title })"
        @update:model-value="emit('toggle-select', map.name)"
      />
    </td>
    <td class="maps-map-list-table-row__cell maps-map-list-table-row__cell--stretch">
      <div class="maps-map-list-table-row__name">
        <MapsLink
          :to="{ view: 'map', name: map.name }"
          class="maps-map-list-table-row__link"
          :title="title"
        >
          {{ title }}
        </MapsLink>
        <!-- The management flags sit with the name; a column of their own would
             be empty for nearly every map. -->
        <MapFlags v-if="auth.isAdmin.value" :map="map" variant="text" />
      </div>
    </td>
    <td v-if="showActions" class="maps-map-list-table-row__cell" @click.stop>
      <MapRowActions
        :map="map"
        variant="inline"
        @clone="emit('clone', $event)"
        @export="emit('export', $event)"
        @delete="emit('delete', $event)"
      />
    </td>
    <td class="maps-map-list-table-row__cell">
      {{ mapTypeLabel(map.view.type, _t) }}
    </td>
    <td class="maps-map-list-table-row__cell maps-map-list-table-row__cell--dimmed">
      {{ mapOwnerLabel(map, auth.user.value?.user_id, _t) }}
    </td>
    <td class="maps-map-list-table-row__cell">
      {{ mapVisibilityLabel(map, _t) }}
    </td>
    <td v-if="showConnection" class="maps-map-list-table-row__cell">
      <MapConnectionLabel :connection-id="map.connection_id" />
    </td>
    <!-- A map whose contents come from the live query has no count to give.
         Which maps those are, the type already says. -->
    <td class="maps-map-list-table-row__cell maps-map-list-table-row__cell--numeric">
      <span v-if="hasDynamicContent(map)" :title="_t('Contents come from the live query')">
        {{ untranslated('—') }}
      </span>
      <span v-else>{{ map.object_count }}</span>
    </td>
  </tr>
</template>

<style scoped>
/* The zebra Checkmk listings use, on the tokens the theme defines for it. */
.maps-map-list-table-row:nth-child(odd) {
  background-color: var(--odd-tr-bg-color);
}

.maps-map-list-table-row:nth-child(even) {
  background-color: var(--even-tr-bg-color);
}

/* Same hover as the monitoring views' rows: the zebra already owns the greys,
   so the row under the pointer has to leave them. */
.maps-map-list-table-row:hover {
  background-color: var(--color-dark-blue-90);
}

body[data-theme='facelift'] .maps-map-list-table-row:hover {
  background-color: var(--color-dark-blue-10);
}

.maps-map-list-table-row--selected,
.maps-map-list-table-row--selected:nth-child(odd),
.maps-map-list-table-row--selected:nth-child(even) {
  background-color: color-mix(in srgb, var(--color-corporate-green-50) 12%, transparent);
}

.maps-map-list-table-row__select,
.maps-map-list-table-row__cell {
  height: 26px;
  padding: var(--dimension-2) var(--dimension-4);
  vertical-align: middle;
  white-space: nowrap;
}

.maps-map-list-table-row__select {
  width: 28px;
}

/* The name column carries the width the others leave. It is the only cell that
   may wrap: a long alias costs a second line here rather than pushing the facts
   to its right off the page. */
.maps-map-list-table-row__cell--stretch {
  white-space: normal;
}

.maps-map-list-table-row__cell--dimmed {
  color: var(--font-color-dimmed);
}

.maps-map-list-table-row__cell--numeric {
  font-variant-numeric: tabular-nums;
  color: var(--font-color-dimmed);
  text-align: right;
}

.maps-map-list-table-row__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4);
  min-width: 0;
}

.maps-map-list-table-row__link {
  color: var(--font-color);
  text-decoration: none;
}

.maps-map-list-table-row__link:hover {
  text-decoration: underline;
}
</style>
