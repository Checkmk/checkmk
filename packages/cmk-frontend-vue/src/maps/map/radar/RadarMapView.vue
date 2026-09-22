<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map that is nothing but the current state of whatever an operator's filter
matches -- a host group, a service group, a tag -- laid out worst first.

Nothing is placed on a radar map, so there is no drawing of its own: the map is
the state stream, so this view reads it directly rather than being handed the
lookup the placed map types work from. What a click on a card leads to is the
map view's, like everywhere else.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import { useStates } from '@/maps/services/context'
import type { MapConfig, MapElement } from '@/maps/types/api'
import { stateWordFromToken } from '@/maps/utils/objectAria'
import { parseFilterTerms } from '@/maps/utils/objectFilter'
import { stateColorVar } from '@/maps/utils/stateColors'

import RadarCard from './components/RadarCard.vue'
import {
  RADAR_UNSUPPORTED_PREFIXES,
  radarMapElement,
  radarName,
  radarStateCounts,
  radarStates
} from './objects'

/** How many cards the settings preview shows before it says how many it left out. */
const PREVIEW_LIMIT = 12

/**
 * How many cards the map itself draws. A radar map's filter can be every host
 * on the site, and each card is a transition and two ``color-mix()`` that the
 * next state tick recomputes, so the grid is bounded like the other lists the
 * SPA fills from a filter and the operator narrows with the search.
 */
const RENDER_LIMIT = 500

const { _t, _tn } = usei18n()
const statesStore = useStates()

const props = defineProps<{
  config: MapConfig | null
  /** Why the map could not be loaded, if it could not. */
  error: string | null
  preview: boolean
  filterNeedle: string
  problemsOnly: boolean
}>()

const emit = defineEmits<{
  'update:filterNeedle': [needle: string]
  'update:problemsOnly': [value: boolean]
  'object-click': [object: MapElement, event?: MouseEvent]
}>()

// A radar map's content arrives with the first state snapshot, so until then
// there is nothing to lay out -- and an empty grid would read as "no matches".
// A snapshot that came back empty is a loaded map with nothing in it, though,
// not a pending one: the daemon reports `connection_ok` false for every empty
// result, so only the absence of a snapshot may hold the spinner.
const awaitingSnapshot = computed(() => statesStore.lastUpdate.value === null)
const loading = computed(
  () => statesStore.initialLoad.value || (awaitingSnapshot.value && !statesStore.loadError.value)
)
// ... and a read that failed must not hold it forever. With no snapshot behind
// it there is nothing to draw, so the reason takes the map's place; once a
// snapshot is up the banner below reports the same thing without losing it.
const unreachable = computed(() => (awaitingSnapshot.value ? statesStore.loadError.value : null))

const matching = computed(() =>
  radarStates(statesStore.states.value, {
    terms: parseFilterTerms(props.filterNeedle),
    problemsOnly: props.problemsOnly
  })
)
const shown = computed(() => matching.value.slice(0, props.preview ? PREVIEW_LIMIT : RENDER_LIMIT))
const omitted = computed(() => matching.value.length - shown.value.length)
// The tallies describe the filter's result, not the slice of it that fits: a
// preview whose criticals sorted past the cut still has to say it has some.
const counts = computed(() => radarStateCounts(matching.value))
</script>

<template>
  <div class="maps-radar-map-view">
    <MapPlaceholder v-if="error" :message="error" variant="error" />

    <template v-else-if="config">
      <div
        class="maps-radar-map-view__stage"
        :class="{ 'maps-radar-map-view__stage--compact': preview }"
      >
        <div v-if="loading" class="maps-radar-map-view__loading">
          <CmkLoading />
        </div>

        <MapPlaceholder v-else-if="unreachable" :message="unreachable" variant="error" />

        <div v-else-if="!matching.length" class="maps-radar-map-view__empty">
          <p class="maps-radar-map-view__empty-title">{{ _t('No objects found') }}</p>
          <p class="maps-radar-map-view__empty-hint">
            {{ _t('Adjust the filter via map settings') }}
          </p>
        </div>

        <template v-else>
          <!-- In flow above the grid rather than over it: a banner across the
               cards would cover the very states it is warning about. -->
          <CmkAlertBox
            v-if="!preview && !statesStore.connected.value"
            variant="warning"
            size="small"
          >
            {{ _t('Connection lost — showing last known state') }}
          </CmkAlertBox>
          <CmkAlertBox
            v-else-if="!preview && statesStore.deadSites.value.length"
            variant="warning"
            size="small"
          >
            {{
              _t('Site unreachable: %{sites} — showing last known state for its hosts', {
                sites: statesStore.deadSites.value.join(', ')
              })
            }}
          </CmkAlertBox>

          <!-- Live: objects come and go as the filter's members change. -->
          <div class="maps-radar-map-view__summary" role="status" :aria-label="_t('Radar summary')">
            <span class="maps-radar-map-view__count">
              {{ _tn('%{n} object', '%{n} objects', matching.length, { n: matching.length }) }}
              <span v-if="omitted > 0" class="maps-radar-map-view__count-note">
                {{ _t('(showing %{n})', { n: shown.length }) }}
              </span>
            </span>
            <div class="maps-radar-map-view__legend">
              <span
                v-for="entry in counts"
                :key="entry.state"
                class="maps-radar-map-view__tally"
                :style="{ '--maps-radar-tally-color': stateColorVar(entry.state) }"
              >
                <span class="maps-radar-map-view__dot" />
                {{ entry.count }} {{ stateWordFromToken(_t, entry.state) }}
              </span>
            </div>
          </div>

          <div class="maps-radar-map-view__grid" role="group" :aria-label="_t('Radar objects')">
            <RadarCard
              v-for="state in shown"
              :key="state.object_id"
              :state="state"
              :name="radarName(state)"
              :compact="preview"
              @activate="(event) => emit('object-click', radarMapElement(state), event)"
            />
            <p v-if="omitted > 0" class="maps-radar-map-view__omitted">
              {{
                preview
                  ? _t('Preview limited — %{hidden} more not shown', { hidden: omitted })
                  : _t('+%{n} more — refine the filter to see them', { n: omitted })
              }}
            </p>
          </div>
        </template>
      </div>

      <MapSearch
        v-if="!preview"
        :model-value="filterNeedle"
        :exclude-prefixes="RADAR_UNSUPPORTED_PREFIXES"
        @update:model-value="emit('update:filterNeedle', $event)"
      >
        <template #trailing>
          <ProblemsOnlyToggle
            :model-value="problemsOnly"
            @update:model-value="emit('update:problemsOnly', $event)"
          />
        </template>
      </MapSearch>
    </template>

    <MapPlaceholder v-else :message="_t('Map not found')" variant="empty" />
  </div>
</template>

<style scoped>
.maps-radar-map-view {
  position: relative;
  flex: 1 1 0%;
  overflow: hidden;
  background: var(--ux-theme-1);
}

.maps-radar-map-view__stage {
  height: 100%;
  overflow: auto;
  padding: var(--dimension-8);
}

.maps-radar-map-view__loading,
.maps-radar-map-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-3);
  height: 100%;
  text-align: center;
  color: var(--font-color-dimmed);
}

.maps-radar-map-view__empty-title {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
}

.maps-radar-map-view__empty-hint {
  font-size: var(--font-size-normal);
  line-height: 16px;
}

.maps-radar-map-view__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-6);
  margin-bottom: var(--dimension-7);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color-dimmed);
}

.maps-radar-map-view__count-note {
  font-style: italic;
}

.maps-radar-map-view__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-5);
}

.maps-radar-map-view__tally {
  display: flex;
  align-items: center;
  gap: 6px;

  /* The state colours are background colours: on the neutral stage WARNING and
     OK are unreadable as ink in the light theme, so the tally mixes far towards
     the theme's font colour and leaves the hue to the dot beside it. */
  color: color-mix(in srgb, var(--maps-radar-tally-color) 40%, var(--font-color));
  font-weight: 500;
}

.maps-radar-map-view__dot {
  width: 6px;
  height: 6px;
  background: var(--maps-radar-tally-color);
  border-radius: 9999px;
}

.maps-radar-map-view__grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.maps-radar-map-view__stage--compact .maps-radar-map-view__grid {
  gap: var(--dimension-3);
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
}

.maps-radar-map-view__omitted {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--font-color-dimmed);
}
</style>
