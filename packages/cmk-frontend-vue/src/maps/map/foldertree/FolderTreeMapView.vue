<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map of the site's own SETUP folder hierarchy, which nobody has to draw: the
daemon sends the tree and this draws it, either as a treemap that fits a whole
site on one screen or as a list that can be read down.

This is the map type's own view: the two drawings and the toolbar over them, the
search and the problems filter they both answer to, the services fetched when a
host is drilled into, and what a right-click on a folder offers. What a click on
a leaf leads to is the map view's, like everywhere else -- but a leaf is not in
the state stream, so it is handed up with the state its tree node carries.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import { useMapViewState } from '@/maps/map/composables/useMapViewState'
import { useObjectHoverMenu } from '@/maps/map/composables/useObjectHoverMenu'
import { useAuth, useStates } from '@/maps/services/context'
import type { FolderTreeNode, MapConfig, MapElement, ObjectState } from '@/maps/types/api'

import FolderBulkActionModal from './components/FolderBulkActionModal.vue'
import FolderContextMenu from './components/FolderContextMenu.vue'
import FolderTreeList from './components/FolderTreeList.vue'
import FolderTreeToolbar from './components/FolderTreeToolbar.vue'
import FolderTreemap from './components/FolderTreemap.vue'
import { useFolderExpansion } from './composables/useFolderExpansion'
import { useFolderServices } from './composables/useFolderServices'
import {
  type FolderQuery,
  type HostStats,
  isFilterActive,
  parseFolderQuery,
  subtreeVisible,
  visibleHostStats,
  visibleServices
} from './filter'
import { folderNodeToElement, folderNodeToState } from './objects'
import { flattenTree } from './rows'

const { _t } = usei18n()
const auth = useAuth()
const states = useStates()
const { problemsOnly, folderView } = useMapViewState()

const props = defineProps<{
  config: MapConfig | null
  /** Why the map could not be loaded, if it could not. */
  error: string | null
  preview: boolean
  kiosk: boolean
  checkmkUrl: string | null
  filterNeedle: string
}>()

const emit = defineEmits<{
  'update:filterNeedle': [needle: string]
  /** A leaf was picked, with the state its tree node carries. */
  select: [object: MapElement, state: ObjectState]
}>()

const view = computed(() => (props.config?.view.type === 'foldertree' ? props.config.view : null))
const showServices = computed(() => view.value?.show_services ?? false)

// A kiosk or wall display forces the treemap: a scrolling list cannot be the
// ambient "always shows the status" surface such a screen is there to be.
const mode = computed({
  get: () => (props.kiosk ? 'map' : folderView.value),
  set: (value) => {
    folderView.value = value
  }
})

const terms = computed(() => parseFolderQuery(props.filterNeedle))

const services = useFolderServices({
  mapName: () => props.config?.name ?? null,
  preview: () => props.preview,
  showServices: () => showServices.value,
  terms: () => terms.value
})

const query = computed<FolderQuery>(() => ({
  terms: terms.value,
  problemsOnly: problemsOnly.value,
  severity: view.value?.problems_severity ?? 'any',
  matchedHosts: services.matchedHosts.value
}))

const canCommand = computed(
  () => auth.mayCommand('acknowledge') || auth.mayCommand('schedule_downtime')
)

/**
 * The hover card the list opens on a leaf. It is the folder tree's own: a leaf
 * is synthesised, so it carries neither a connection nor a template a macro
 * could be expanded against, and the card is told so once here rather than the
 * page having to know it. (The treemap has its own tooltip on the tile.)
 */
const hover = useObjectHoverMenu()

const tree = computed<FolderTreeNode | null>(() => states.folderTree.value)
const expansion = useFolderExpansion(
  tree,
  () => view.value?.default_expand_depth ?? 1,
  () => props.config?.name ?? null
)

// Both drawings show the real root as their top level, so the hierarchy reads
// like Checkmk's own SETUP tree and root-level hosts sit under Main rather than
// floating. A standalone backend has no root .wato to take a title from, so the
// root is named here -- once, for everything that goes on to render it.
const root = computed<FolderTreeNode | null>(() => {
  const raw = tree.value
  if (!raw) {
    return null
  }
  return raw.title ? raw : { ...raw, title: _t('Main') }
})

const summary = computed<HostStats>(() => {
  void states.folderTreeVersion.value // re-derive when the tree is patched in place
  const root = tree.value
  if (!root) {
    return { hosts: 0, counts: {} }
  }
  if (!isFilterActive(query.value)) {
    return { hosts: root.host_count, counts: root.severity_counts }
  }
  return visibleHostStats(root, query.value)
})

// A filter is on and nothing is left -- as opposed to the server search not
// having answered yet, where the previous matches stay and this is held back so
// the tree does not flash empty mid-typing.
const nothingMatches = computed(() => {
  void states.folderTreeVersion.value // re-derive when the tree is patched in place
  const root = tree.value
  return (
    !!root &&
    isFilterActive(query.value) &&
    // Not "no hosts left": an empty folder matched by its own name is still
    // drawn, and both drawings ask this same question about their root.
    !subtreeVisible(root, query.value) &&
    !services.unsettled.value
  )
})

const multiSite = computed(() => {
  const sites = new Set<string>()
  const walk = (node: FolderTreeNode): void => {
    if (node.kind === 'host' && node.site_id) {
      sites.add(node.site_id)
    }
    node.children.forEach(walk)
  }
  if (tree.value) {
    walk(tree.value)
  }
  return sites.size > 1
})

const servicesOf = (host: FolderTreeNode, hostMatched: boolean): FolderTreeNode[] =>
  visibleServices(host.title, services.byHost.value[host.title] ?? [], query.value, hostMatched)

const rows = computed(() => {
  void states.folderTreeVersion.value
  if (!root.value) {
    return []
  }
  return flattenTree(root.value, {
    query: query.value,
    expanded: expansion.expanded,
    showServices: showServices.value,
    servicesOf,
    childrenOf: (folder, folderMatched) =>
      isFilterActive(query.value)
        ? folder.children.filter((child) => subtreeVisible(child, query.value, folderMatched))
        : folder.children,
    serviceLoading: services.loading,
    serviceError: services.failed
  })
})

function clearFilter(): void {
  emit('update:filterNeedle', '')
  problemsOnly.value = false
}

function onToggle(node: FolderTreeNode): void {
  expansion.toggle(node.path)
  if (node.kind === 'host') {
    void services.ensure(node)
  }
}

/** A leaf was picked. `host` names the host a service leaf runs on, else null. */
function onSelect(host: string | null, node: FolderTreeNode): void {
  if (props.preview) {
    return
  }
  emit('select', folderNodeToElement(node, host), folderNodeToState(node, host))
}

function onHover(host: string | null, node: FolderTreeNode, x: number, y: number): void {
  hover.open(folderNodeToElement(node, host), null, {
    x: x + 12,
    y: y + 12,
    anchorRect: null,
    stateOverride: folderNodeToState(node, host)
  })
}

const folderMenu = ref<{ node: FolderTreeNode; x: number; y: number } | null>(null)
const bulkFolder = ref<FolderTreeNode | null>(null)

function onFolderMenu(node: FolderTreeNode, x: number, y: number): void {
  // The settings preview is not interactive, and a read-only display (click
  // action "none") gets no menu -- the same gate a click is under.
  if (props.preview || props.config?.click_action === 'none') {
    return
  }
  hover.close()
  folderMenu.value = { node, x, y }
}

function onBulkCommand(): void {
  bulkFolder.value = folderMenu.value?.node ?? null
  folderMenu.value = null
}

// The view is reused when the map changes, so nothing opened over the previous
// folder tree may still be standing over the next one -- a bulk command least
// of all, which would go out over the hosts of a map no longer on screen.
watch(
  () => props.config?.name,
  () => {
    hover.close()
    folderMenu.value = null
    bulkFolder.value = null
  }
)

function closeBulkModal(): void {
  bulkFolder.value = null
  // The command's effect reaches monitoring a moment later, so closing asks the
  // state stream for a fresh picture.
  states.refreshAfterCommand()
}
</script>

<template>
  <div class="maps-folder-tree-map-view">
    <MapPlaceholder v-if="error" :message="error" variant="error" />

    <template v-else-if="config">
      <!-- On a kiosk screen too, where the map's header is gone: the counts and
           the search are what someone walking up to the wall display reads. -->
      <FolderTreeToolbar
        v-if="!preview"
        v-model:mode="mode"
        v-model:problems-only="problemsOnly"
        :kiosk="kiosk"
        :summary="summary"
        :filtered="isFilterActive(query)"
        :truncated="services.truncated.value"
        :filter-needle="filterNeedle"
        @update:filter-needle="emit('update:filterNeedle', $event)"
        @expand-all="expansion.expandAll()"
        @collapse-all="expansion.collapseAll()"
      />

      <!-- In flow rather than floating: a banner over the drawing would cover
           the very tiles it is warning about. -->
      <CmkAlertBox
        v-if="!preview && root && !states.connected.value"
        variant="warning"
        size="small"
      >
        {{ _t('Connection lost — showing last known state') }}
      </CmkAlertBox>
      <CmkAlertBox
        v-else-if="!preview && root && states.deadSites.value.length"
        variant="warning"
        size="small"
      >
        {{
          _t('Site unreachable: %{sites} — showing last known state for its hosts', {
            sites: states.deadSites.value.join(', ')
          })
        }}
      </CmkAlertBox>

      <div v-if="!root" class="maps-folder-tree-map-view__note">
        {{ _t('Waiting for folder data…') }}
      </div>
      <div v-else-if="!root.children.length" class="maps-folder-tree-map-view__note">
        {{
          _t(
            'No folders to show. The selected connection has no SETUP folders, or your filters hide them.'
          )
        }}
      </div>
      <div v-else-if="nothingMatches" class="maps-folder-tree-map-view__note">
        <span>
          {{
            problemsOnly && query.terms.length === 0
              ? _t('No problems — everything is OK.')
              : _t('No matches for the current filter.')
          }}
        </span>
        <CmkButton variant="optional" size="small" @click="clearFilter">
          {{ _t('Clear filter') }}
        </CmkButton>
      </div>

      <FolderTreemap
        v-else-if="mode === 'map'"
        :root="root"
        :query="query"
        :expansion="expansion"
        :show-services="showServices"
        :services-by-host="services.byHost.value"
        :service-loading="services.loading"
        :service-error="services.failed"
        @expand-host="services.ensure($event)"
        @select="onSelect"
        @ctx-folder="onFolderMenu"
      />
      <FolderTreeList
        v-else
        :rows="rows"
        :rev="states.folderTreeVersion.value"
        :multi-site="multiSite"
        :problems-only="problemsOnly"
        @toggle="onToggle"
        @select="onSelect"
        @hover="onHover"
        @hover-clear="hover.scheduleClose()"
        @ctx-folder="onFolderMenu"
      />

      <!-- A leaf is synthesised: it has no connection and no hover template a
           macro could be expanded against, so the card falls back to its own. -->
      <HoverMenu
        v-if="hover.hover.visible && hover.hover.object"
        :object="hover.hover.object"
        :state="hover.state.value"
        :x="hover.hover.x"
        :y="hover.hover.y"
        :anchor-rect="hover.hover.anchorRect"
        :connection-id="null"
        :checkmk-url="checkmkUrl"
        :template="null"
        @card-enter="hover.cancelClose()"
        @card-leave="hover.scheduleClose()"
      />

      <FolderContextMenu
        v-if="folderMenu"
        :folder="folderMenu.node"
        :x="folderMenu.x"
        :y="folderMenu.y"
        :checkmk-url="checkmkUrl"
        :can-command="canCommand"
        @close="folderMenu = null"
        @bulk-command="onBulkCommand"
      />
      <FolderBulkActionModal v-if="bulkFolder" :folder="bulkFolder" @close="closeBulkModal" />
    </template>

    <MapPlaceholder v-else :message="_t('Map not found')" variant="empty" />
  </div>
</template>

<style scoped>
.maps-folder-tree-map-view {
  display: flex;
  flex: 1 1 0%;
  flex-direction: column;
  overflow: hidden;
  background: var(--ux-theme-1);
}

.maps-folder-tree-map-view__note {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-5);
  padding: var(--dimension-8);
  font-size: 13px;
  color: var(--font-color-dimmed);
  text-align: center;
}
</style>
