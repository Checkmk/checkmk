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
import { computed } from 'vue'

import MapsMenu from '@/maps/shared/components/MapsMenu.vue'
import MapsMenuItem from '@/maps/shared/components/MapsMenuItem.vue'
import type { FolderTreeNode } from '@/maps/types/api'
import { stripCheckmkBase } from '@/maps/utils/mapNavigation'

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
  <MapsMenu
    :x="x"
    :y="y"
    :label="folder.title"
    :heading="folder.title"
    :subheading="_t('Folder')"
    @click.stop
    @close="emit('close')"
  >
    <MapsMenuItem v-if="offersCommands" @click="emit('bulk-command')">
      <CmkIcon name="checkmark" size="small" />
      <span>{{ _t('Folder actions') }}</span>
    </MapsMenuItem>
    <MapsMenuItem v-if="setupUrl" :href="setupUrl" @click="emit('close')">
      <CmkIcon name="export-link" size="small" />
      <span>{{ _t('Open in Checkmk Setup') }}</span>
    </MapsMenuItem>
    <div v-if="!offersCommands && !setupUrl" class="maps-folder-context-menu__empty">
      {{ _t('No Checkmk URL configured') }}
    </div>
  </MapsMenu>
</template>

<style scoped>
.maps-folder-context-menu__backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}

.maps-folder-context-menu__empty {
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--font-color-dimmed);
}
</style>
