<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a right-click on a folder offers: the two things an operator does to a
whole folder rather than to one host in it -- take all of it out of monitoring
for a while, or go and change it in Setup.

A folder is not a map object, so this is not the object context menu the other
map types open; it is the folder tree's own.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, useTemplateRef } from 'vue'

import { useEscapeClose } from '@/maps/shared/composables/useEscapeClose'
import type { FolderTreeNode } from '@/maps/types/api'
import { stripCheckmkBase } from '@/maps/utils/mapNavigation'
import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'

const props = defineProps<{
  folder: FolderTreeNode
  /** Where the operator right-clicked. */
  x: number
  y: number
  checkmkUrl: string | null
  /** Whether this operator may send commands at all. */
  canCommand: boolean
}>()

const emit = defineEmits<{ close: []; 'bulk-command': [] }>()

const { _t } = usei18n()

const menuEl = useTemplateRef('menuEl')
const menuStyle = usePointerOverlayStyle(menuEl, () => ({ x: props.x, y: props.y }))

// A right-click leaves the focus on the tile or row it came from, so a key
// bound on the menu itself would never be reached. Escape is bound on the
// window instead, the same way every other dismissable surface here does it.
useEscapeClose(() => emit('close'))

const offersCommands = computed(() => props.canCommand && props.folder.host_count > 0)

// wato.py addresses a folder by its path relative to Main, which is what the
// tree node carries.
const setupUrl = computed(() => {
  if (!props.checkmkUrl) {
    return null
  }
  const query = new URLSearchParams({ mode: 'folder', folder: props.folder.path })
  return `${stripCheckmkBase(props.checkmkUrl)}/check_mk/wato.py?${query.toString()}`
})
</script>

<template>
  <!-- Pointer-only dismiss layer; the keyboard closes with Escape. -->
  <div
    class="maps-folder-context-menu__backdrop"
    aria-hidden="true"
    @click="emit('close')"
    @contextmenu.prevent="emit('close')"
  />
  <div ref="menuEl" class="maps-folder-context-menu" :style="menuStyle" @click.stop>
    <div class="maps-folder-context-menu__header">
      <p class="maps-folder-context-menu__name">{{ folder.title }}</p>
      <p class="maps-folder-context-menu__type">{{ _t('Folder') }}</p>
    </div>
    <button
      v-if="offersCommands"
      type="button"
      class="maps-folder-context-menu__item"
      @click="emit('bulk-command')"
    >
      <CmkIcon name="checkmark" size="small" />
      <span>{{ _t('Folder actions') }}</span>
    </button>
    <a
      v-if="setupUrl"
      :href="setupUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="maps-folder-context-menu__item"
      @click="emit('close')"
    >
      <CmkIcon name="export-link" size="small" />
      <span>{{ _t('Open in Checkmk Setup') }}</span>
    </a>
    <div v-if="!offersCommands && !setupUrl" class="maps-folder-context-menu__empty">
      {{ _t('No Checkmk URL configured') }}
    </div>
  </div>
</template>

<style scoped>
.maps-folder-context-menu__backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}

/* Pointer position, so the menu opens where the operator right-clicked. */
.maps-folder-context-menu {
  position: fixed;
  z-index: 50;
  width: max-content;
  min-width: 224px;
  max-width: calc(100% - 16px);
  padding: 6px 0;
  background: var(--maps-map-view-glass);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
  backdrop-filter: blur(12px);
}

.maps-folder-context-menu__header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  border-bottom: 1px solid var(--default-border-color);
}

.maps-folder-context-menu__name {
  overflow: hidden;
  max-width: 208px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-folder-context-menu__type {
  margin-top: var(--dimension-2);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-folder-context-menu__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color-dimmed);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.maps-folder-context-menu__item:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-folder-context-menu__empty {
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--font-color-dimmed);
}
</style>
