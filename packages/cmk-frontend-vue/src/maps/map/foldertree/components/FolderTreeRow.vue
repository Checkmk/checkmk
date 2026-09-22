<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One line of the folder tree's list: a folder, a host, or a service.

Purely presentational. The tree is flattened and windowed before it gets here,
so the row does not recurse and does not decide what is open -- its depth and
its openness are handed to it, and everything it can be asked to do it asks
upwards.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { FolderTreeNode } from '@/maps/types/api'
import { stateWordFromToken } from '@/maps/utils/objectAria'
import { type SeverityPill, severityPills, stateColorVar } from '@/maps/utils/stateColors'

const props = defineProps<{
  node: FolderTreeNode
  /**
   * The tree's nodes are patched in place, so a bumped revision is what tells
   * the row that its live status changed.
   */
  rev: number
  depth: number
  isOpen: boolean
  isExpandable: boolean
  /** Whether hosts are worth labelling with the site they are monitored from. */
  multiSite: boolean
  /** The owning host, so a service row's click can resolve it. */
  hostName?: string
}>()

const emit = defineEmits<{
  toggle: [FolderTreeNode]
  /** A leaf was picked. `host` names the host a service runs on, else null. */
  select: [host: string | null, node: FolderTreeNode]
  hover: [host: string | null, node: FolderTreeNode, x: number, y: number]
  'hover-clear': []
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const { _t, _tn } = usei18n()

const stateWord = (state: string): string => stateWordFromToken(_t, state)

function pillTitle(pill: SeverityPill): string {
  return _tn('%{n} %{state} host', '%{n} %{state} hosts', pill.count, {
    n: pill.count,
    state: stateWord(pill.state)
  })
}

const isEmptyFolder = computed(() => {
  void props.rev
  return props.node.kind === 'folder' && props.node.is_empty
})
const pills = computed(() => {
  void props.rev
  return severityPills(props.node.severity_counts)
})
// The healthy remainder, so the pill breakdown adds up to the host count.
const healthy = computed(() => {
  void props.rev
  return Math.max(0, props.node.host_count - props.node.problem_count)
})

function onClick(): void {
  if (props.node.kind === 'host') {
    emit('select', null, props.node)
  } else if (props.node.kind === 'service') {
    emit('select', props.hostName ?? '', props.node)
  } else {
    emit('toggle', props.node)
  }
}

// Anchored on the cursor: rows are full-width, so a row-shaped anchor would
// overflow and flip the card over the navigation.
function onHover(event: MouseEvent): void {
  if (props.node.kind === 'host') {
    emit('hover', null, props.node, event.clientX, event.clientY)
  } else if (props.node.kind === 'service') {
    emit('hover', props.hostName ?? '', props.node, event.clientX, event.clientY)
  }
}

// Folders only; a host or service row keeps the browser's own menu.
function onContextMenu(event: MouseEvent): void {
  if (props.node.kind !== 'folder') {
    return
  }
  event.preventDefault()
  emit('ctx-folder', props.node, event.clientX, event.clientY)
}
</script>

<template>
  <!-- The keys are bound with `.self`: a key pressed on the chevron inside has
       to reach the chevron's own button rather than be prevented here and
       re-read as a click on the row. -->
  <div
    class="maps-folder-tree-row"
    :class="{
      'maps-folder-tree-row--folder': node.kind === 'folder',
      'maps-folder-tree-row--stale': node.stale
    }"
    role="treeitem"
    tabindex="0"
    :aria-level="depth + 1"
    :aria-expanded="isExpandable ? isOpen : undefined"
    :title="node.output || undefined"
    @click="onClick"
    @keydown.enter.self.prevent="onClick"
    @keydown.space.self.prevent="onClick"
    @contextmenu="onContextMenu"
    @mousemove="onHover"
    @mouseleave="emit('hover-clear')"
  >
    <!-- One vertical guide per ancestor level, so the nesting depth -- a host
         directly under Main against one inside a subfolder -- is unambiguous. -->
    <span v-for="level in depth" :key="level" class="maps-folder-tree-row__guide" />
    <!-- Anything that can be drilled into gets a chevron, so the drill-down is
         discoverable; a leaf gets a spacer of the same width. -->
    <button
      v-if="isExpandable"
      type="button"
      class="maps-folder-tree-row__chevron"
      :aria-label="isOpen ? _t('Collapse') : _t('Expand')"
      @click.stop="emit('toggle', node)"
    >
      {{ isOpen ? '▾' : '▸' }}
    </button>
    <span v-else class="maps-folder-tree-row__chevron maps-folder-tree-row__chevron--spacer" />

    <CmkIcon
      v-if="node.kind === 'folder'"
      :name="isOpen ? 'folder-open' : 'folder'"
      size="medium"
      :class="{ 'maps-folder-tree-row__icon--empty': isEmptyFolder }"
    />
    <CmkIcon v-else-if="node.kind === 'host'" name="host" size="medium" />
    <span
      v-if="!isEmptyFolder && !(node.kind === 'folder' && pills.length)"
      class="maps-folder-tree-row__dot"
      :style="{ background: stateColorVar(node.state) }"
      :title="stateWord(node.state)"
    />

    <span
      class="maps-folder-tree-row__title"
      :class="{
        'maps-folder-tree-row__title--empty': isEmptyFolder,
        'maps-folder-tree-row__title--service': node.kind === 'service'
      }"
      >{{ node.title }}</span
    >

    <!-- Kept next to the name: a right-aligned count drifts away on a wide screen. -->
    <span
      v-if="isEmptyFolder"
      class="maps-folder-tree-row__badge maps-folder-tree-row__badge--empty"
      >{{ _t('empty · 0 hosts') }}</span
    >
    <span v-else-if="node.kind === 'folder'" class="maps-folder-tree-row__meta"
      >{{ _tn('%{n} host', '%{n} hosts', node.host_count, { n: node.host_count })
      }}<template v-if="pills.length && healthy > 0">
        · {{ healthy }} {{ _t('OK') }}</template
      ></span
    >
    <span v-if="node.kind === 'folder' && pills.length" class="maps-folder-tree-row__pills">
      <span
        v-for="pill in pills"
        :key="pill.state"
        class="maps-folder-tree-row__pill"
        :style="{ background: pill.bg, color: pill.fg }"
        :title="pillTitle(pill)"
        >{{ pill.count }}</span
      >
    </span>

    <span class="maps-folder-tree-row__fill" />

    <span
      v-if="node.stale"
      class="maps-folder-tree-row__badge maps-folder-tree-row__badge--stale"
      :title="_t('Site unreachable — last known state')"
      >{{ _t('stale') }}</span
    >
    <span
      v-if="node.kind === 'host' && multiSite && node.site_id"
      class="maps-folder-tree-row__site"
      >{{ node.site_id }}</span
    >
  </div>
</template>

<style scoped>
.maps-folder-tree-row {
  display: flex;
  align-items: center;
  gap: 7px;

  /* Must match the list's row height, which drives the windowing. */
  height: var(--maps-folder-tree-row-height, 28px);
  padding-left: 6px;
  font-size: 13px;
  color: var(--font-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  user-select: none;
}

/* One per ancestor level: an 18px column with a guide down its left edge. The
   negative margin cancels the row's 7px gap so the columns stay 18px wide. */
.maps-folder-tree-row__guide {
  width: 18px;
  flex-shrink: 0;
  align-self: stretch;
  margin-right: -7px;
  border-left: 1px solid var(--default-border-color);
}

.maps-folder-tree-row--folder {
  font-weight: 500;
}

.maps-folder-tree-row:hover {
  background: var(--input-hover-bg-color);
}

.maps-folder-tree-row:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: -2px;
}

.maps-folder-tree-row__chevron {
  width: 16px;
  flex-shrink: 0;
  padding: 0;
  font-size: 11px;
  color: var(--font-color-dimmed);
  background: transparent;
  border: none;
  cursor: pointer;
}

.maps-folder-tree-row__chevron--spacer {
  cursor: default;
}

.maps-folder-tree-row__icon--empty {
  opacity: 0.45;
}

.maps-folder-tree-row__dot {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-folder-tree-row__title {
  overflow: hidden;
  flex-shrink: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* A service name may use the full row width -- the plugin output moved to the
   hover card -- but still ellipsizes when very long. */
.maps-folder-tree-row__title--service {
  flex-shrink: 1;
  font-weight: 400;
}

.maps-folder-tree-row__title--empty {
  font-style: italic;
  font-weight: 400;
  color: var(--font-color-dimmed);
}

/* Fills the row so the trailing site badge right-aligns. */
.maps-folder-tree-row__fill {
  flex: 1;
  min-width: 0;
}

.maps-folder-tree-row__meta {
  font-size: 11px;
  color: var(--font-color-dimmed);
}

.maps-folder-tree-row__badge {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: var(--font-size-small);
  border-radius: 9px;
}

.maps-folder-tree-row__badge--empty {
  color: var(--font-color-dimmed);
  border: 1px dashed var(--default-border-color);
}

/* Per-site trust: a leaf frozen on its last known state, its site being down. */
.maps-folder-tree-row__badge--stale {
  color: var(--font-color-dimmed);
  border: 1px solid var(--default-border-color);
}

.maps-folder-tree-row--stale {
  opacity: 0.55;
}

.maps-folder-tree-row__pills {
  display: inline-flex;
  flex-shrink: 0;
  gap: 3px;
}

.maps-folder-tree-row__pill {
  min-width: 16px;
  padding: 2px 6px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  line-height: 1;
  text-align: center;
  border-radius: 9px;
}

.maps-folder-tree-row__site {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
}
</style>
