<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The folder tree's own toolbar: what is on screen, on the left, and what can be
done to it, on the right.

A reserved bar under the map's header rather than the floating controls the
other map types use. The treemap fills its stage and the list is a full-width
scroller, so anything floating would sit on top of the data instead of beside
it. Being its own band is also what keeps it on a kiosk screen, where the
header itself is gone.

Every control here is quieter than the search beside it: Checkmk's icon
buttons and toggle group at their small size.
Giving all of them the search's weight would leave the bar shouting its own
chrome at the operator instead of the map's state.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import MapSearch from '@/maps/map/components/MapSearch.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import type { FolderTreeView } from '@/maps/types/api'
import { stateShortWordFromToken } from '@/maps/utils/objectAria'
import { severityPills } from '@/maps/utils/stateColors'

import type { HostStats } from '../filter'

/** Which of the folder tree's two drawings is on screen. */
type FolderTreeMode = FolderTreeView['default_view']

const props = defineProps<{
  /** The hosts on screen, and how their problems break down. */
  summary: HostStats
  /** Whether that is a filtered count rather than the whole tree. */
  filtered: boolean
  /** Whether the server had more search matches than it would return. */
  truncated: boolean
  mode: FolderTreeMode
  filterNeedle: string
  problemsOnly: boolean
  /** A wall display, which is pinned to the treemap and has no view to choose. */
  kiosk: boolean
  /** Whether a text search is on, which opens every folder on the way to a
   *  match by itself. */
  searching: boolean
  /** Whether expanding, or collapsing, all would change anything. */
  canExpandAll: boolean
  canCollapseAll: boolean
}>()

const emit = defineEmits<{
  'update:mode': [FolderTreeMode]
  'update:filterNeedle': [needle: string]
  'update:problemsOnly': [value: boolean]
  'expand-all': []
  'collapse-all': []
}>()

const { _t, _tn } = usei18n()

const pills = computed(() => severityPills(props.summary.counts))
// The healthy remainder, so the breakdown adds up to the host count.
const healthy = computed(() =>
  Math.max(
    0,
    props.summary.hosts - Object.values(props.summary.counts).reduce((sum, n) => sum + n, 0)
  )
)

// A search opens every folder on the way to a match, so neither button has
// anything to act on until it is cleared -- which the operator is told.
const searchingHint = computed(() =>
  props.searching ? _t('Clear the search to open and close folders yourself') : undefined
)

const modes = computed<{ label: TranslatedString; value: FolderTreeMode }[]>(() => [
  { label: _t('Map'), value: 'map' },
  { label: _t('List'), value: 'list' }
])

// The group hands back a plain string; the option it came from carries the type.
function selectMode(value: string): void {
  const picked = modes.value.find((option) => option.value === value)
  if (picked) {
    emit('update:mode', picked.value)
  }
}
</script>

<template>
  <div class="maps-folder-tree-toolbar">
    <span class="maps-folder-tree-toolbar__summary">
      <span>
        {{
          filtered
            ? _tn('showing %{n} host', 'showing %{n} hosts', summary.hosts, { n: summary.hosts })
            : _tn('%{n} host', '%{n} hosts', summary.hosts, { n: summary.hosts })
        }}
      </span>
      <span v-if="pills.length && healthy > 0" class="maps-folder-tree-toolbar__quiet"
        >· {{ healthy }} {{ _t('OK') }}</span
      >
      <span
        v-for="pill in pills"
        :key="pill.state"
        class="maps-folder-tree-toolbar__pill"
        :style="{ background: pill.bg, color: pill.fg }"
        >{{ pill.count }} {{ stateShortWordFromToken(_t, pill.state) }}</span
      >
      <!-- Nothing on screen is not everything being fine. -->
      <span v-if="!pills.length && summary.hosts > 0" class="maps-folder-tree-toolbar__quiet"
        >· {{ _t('all OK') }}</span
      >
      <span v-if="truncated" class="maps-folder-tree-toolbar__truncated">
        {{ _t('more matches exist — refine your search') }}
      </span>
    </span>

    <span class="maps-folder-tree-toolbar__spacer" />

    <!-- The two filters side by side, and the input holding nothing but input:
         what to look for, and whether to look at healthy objects at all, are
         one thought in two controls. -->
    <span class="maps-folder-tree-toolbar__group">
      <MapSearch
        inline
        :model-value="filterNeedle"
        :placeholder="_t('Search folders, hosts, services…')"
        :exclude-prefixes="['hg', 'sg', 'id']"
        @update:model-value="emit('update:filterNeedle', $event)"
      />
      <ProblemsOnlyToggle
        :model-value="problemsOnly"
        :title="_t('Show only folders/hosts with problems')"
        @update:model-value="emit('update:problemsOnly', $event)"
      />
    </span>

    <!-- The view switch rightmost, as in Checkmk. -->
    <span class="maps-folder-tree-toolbar__group maps-folder-tree-toolbar__group--view">
      <!-- Disabled rather than hidden where they would do nothing, so the
           other one does not slide under a second click. -->
      <CmkButton
        variant="text"
        size="iconOnly"
        :aria-label="_t('Expand all')"
        :disabled="searching || !canExpandAll"
        :disabled-reason="searchingHint"
        :title="_t('Expand all folders')"
        @click="emit('expand-all')"
      >
        <CmkMultitoneIcon name="chevron-down" primary-color="font" size="small" />
      </CmkButton>
      <CmkButton
        variant="text"
        size="iconOnly"
        :aria-label="_t('Collapse all')"
        :disabled="searching || !canCollapseAll"
        :disabled-reason="searchingHint"
        :title="_t('Collapse all folders except Main')"
        @click="emit('collapse-all')"
      >
        <CmkMultitoneIcon name="chevron-up" primary-color="font" size="small" />
      </CmkButton>
      <CmkToggleButtonGroup
        v-if="!kiosk"
        role="group"
        :aria-label="_t('Folder tree drawing')"
        :model-value="mode"
        :options="modes"
        size="small"
        spacing="none"
        @update:model-value="selectMode"
      />
    </span>
  </div>
</template>

<style scoped>
/* Wraps onto a second line on a narrow map rather than clipping, and never
   covers the drawing below it. */
.maps-folder-tree-toolbar {
  display: flex;
  flex-wrap: wrap;
  flex-shrink: 0;
  align-items: center;
  gap: var(--dimension-4);
  min-height: 44px;
  padding: 6px 12px;
  background: var(--ux-theme-3);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-folder-tree-toolbar__spacer {
  flex: 1;
}

/* Controls that belong together wrap onto the next line as one, rather than
   the search ending up on one line and its problems filter on the next. A
   group alone on a line too narrow for it wraps inside instead of clipping. */
.maps-folder-tree-toolbar__group {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4);
  min-width: 0;
}

.maps-folder-tree-toolbar__group--view {
  margin-left: var(--dimension-4);
}

.maps-folder-tree-toolbar__summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-folder-tree-toolbar__quiet {
  color: var(--font-color-dimmed);
}

.maps-folder-tree-toolbar__pill {
  padding: 2px 7px;
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  line-height: 1;
  border-radius: 9px;
}

.maps-folder-tree-toolbar__truncated {
  font-weight: var(--font-weight-bold);
  color: var(--color-state-warning);
}
</style>
