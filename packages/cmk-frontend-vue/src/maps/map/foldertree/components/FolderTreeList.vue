<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The folder tree as an indented list.

A site can have a hundred thousand hosts, so only the rows the viewport covers
are in the DOM: a spacer of the full height drives the scrollbar, and the
rendered window is translated into place. Every row is the same height, which is
what makes that windowing a division rather than a measurement.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref, useTemplateRef, watch } from 'vue'

import type { FolderTreeNode } from '@/maps/types/api'

import type { FlatRow } from '../rows'
import FolderTreeRow from './FolderTreeRow.vue'

/** Row height in px. The row's own CSS is driven from here, so the windowing
 *  arithmetic and the rendering cannot drift apart. */
const ROW_HEIGHT = 28
/** Rows rendered beyond the viewport, so a scroll does not show a blank band. */
const OVERSCAN = 10

const props = defineProps<{
  rows: FlatRow[]
  /** Bumped when the tree is patched in place, so rows re-derive their status. */
  rev: number
  multiSite: boolean
  /** Whether the "no services" note should say "no problem services" instead. */
  problemsOnly: boolean
}>()

const emit = defineEmits<{
  toggle: [FolderTreeNode]
  /** A leaf was picked. `host` names the host a service runs on, else null. */
  select: [host: string | null, node: FolderTreeNode]
  hover: [host: string | null, node: FolderTreeNode, x: number, y: number]
  'hover-clear': []
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const { _t } = usei18n()

const scrollEl = useTemplateRef<HTMLDivElement>('scrollEl')
const scrollTop = ref(0)
const viewportHeight = ref(0)

const totalHeight = computed(() => props.rows.length * ROW_HEIGHT)
// Clamped to the list's length, so a list that shrinks while scrolled down --
// a collapse-all, a filter -- cannot leave the window past the end and blank.
const firstIndex = computed(() =>
  Math.max(0, Math.min(Math.floor(scrollTop.value / ROW_HEIGHT) - OVERSCAN, props.rows.length - 1))
)
const lastIndex = computed(() =>
  Math.min(
    props.rows.length,
    Math.ceil((scrollTop.value + viewportHeight.value) / ROW_HEIGHT) + OVERSCAN
  )
)
const visibleRows = computed(() => props.rows.slice(firstIndex.value, lastIndex.value))
const offset = computed(() => firstIndex.value * ROW_HEIGHT)

function noteLabel(row: FlatRow): string {
  if (row.note === 'loading') {
    return _t('Loading services…')
  }
  if (row.note === 'error') {
    return _t('Could not load services')
  }
  return props.problemsOnly ? _t('No problem services') : _t('No services')
}

// FolderTreeRow's optional `hostName` rejects an explicit `undefined` under
// exactOptionalPropertyTypes, so it is spread in only when there is one.
function hostNameProp(row: FlatRow): { hostName?: string } {
  return row.hostName === undefined ? {} : { hostName: row.hostName }
}

// The viewport the windowing measures against. It appears on a switch back
// from the treemap, and changes with the browser window.
useResizeObserver(() => {
  viewportHeight.value = scrollEl.value?.clientHeight ?? 0
}).observe(scrollEl)

// jsdom, and a browser before the first resize callback, report nothing, so the
// height is read once when the element arrives rather than waited for.
watch(scrollEl, (element) => {
  viewportHeight.value = element?.clientHeight ?? 0
  scrollTop.value = element?.scrollTop ?? 0
})
</script>

<template>
  <div
    ref="scrollEl"
    class="maps-folder-tree-list"
    role="tree"
    :style="{ '--maps-folder-tree-row-height': `${ROW_HEIGHT}px` }"
    @scroll="scrollTop = scrollEl?.scrollTop ?? 0"
  >
    <div class="maps-folder-tree-list__spacer" :style="{ height: `${totalHeight}px` }">
      <div class="maps-folder-tree-list__window" :style="{ transform: `translateY(${offset}px)` }">
        <template v-for="row in visibleRows" :key="row.key">
          <div
            v-if="row.note"
            class="maps-folder-tree-list__note"
            :class="{ 'maps-folder-tree-list__note--error': row.note === 'error' }"
            :style="{ paddingLeft: `${row.depth * 18 + 16}px` }"
          >
            {{ noteLabel(row) }}
          </div>
          <FolderTreeRow
            v-else
            :node="row.node"
            :rev="rev"
            :depth="row.depth"
            :is-open="row.isOpen"
            :is-expandable="row.isExpandable"
            :multi-site="multiSite"
            v-bind="hostNameProp(row)"
            @toggle="emit('toggle', $event)"
            @select="(host, node) => emit('select', host, node)"
            @hover="(host, node, x, y) => emit('hover', host, node, x, y)"
            @hover-clear="emit('hover-clear')"
            @ctx-folder="(node, x, y) => emit('ctx-folder', node, x, y)"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-folder-tree-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;

  /* No vertical padding: the scroll offset has to map straight onto a row index. */
  padding: 0 8px;
}

.maps-folder-tree-list__spacer {
  position: relative;
}

.maps-folder-tree-list__window {
  position: absolute;
  inset: 0 0 auto;
}

.maps-folder-tree-list__note {
  display: flex;
  align-items: center;
  height: var(--maps-folder-tree-row-height);
  font-size: var(--font-size-normal);
  font-style: italic;
  color: var(--font-color-dimmed);
}

.maps-folder-tree-list__note--error {
  font-style: normal;
  color: var(--color-state-critical);
}
</style>
