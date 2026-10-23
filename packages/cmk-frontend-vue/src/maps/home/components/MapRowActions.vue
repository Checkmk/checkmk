<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What you can do to a listed map: clone it, export it, delete it. The card grid
and the table offer the same three, so they render the same component; each
entry appears only where this user may use it on this map.

How they are offered follows what the surrounding surface does. A table row
shows them as icon buttons, the way Checkmk's own Customize listings do (see
pagetypes' _show_table) and the monitoring views' action cell. A card has no
column to spend on them and keeps the overflow menu.
-->
<script setup lang="ts">
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { DropdownMenuItem } from 'reka-ui'
import { computed } from 'vue'

import { useAuth } from '@/maps/services/context'
import MapsOverflowMenu from '@/maps/shared/components/MapsOverflowMenu.vue'
import type { MapRead } from '@/maps/types/api'

interface RowAction {
  id: 'clone' | 'export' | 'delete'
  label: TranslatedString
  icon: SimpleIcons
  /** What the icon button is called: every row carries the same three. */
  buttonLabel: TranslatedString
  run: () => void
}

const props = withDefaults(defineProps<{ map: MapRead; variant?: 'menu' | 'inline' }>(), {
  variant: 'menu'
})

const emit = defineEmits<{
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { _t } = usei18n()
const auth = useAuth()

const title = computed(() => props.map.alias || props.map.name)

const actions = computed<RowAction[]>(() => {
  const available: RowAction[] = []
  if (auth.canCreateMaps.value) {
    available.push({
      id: 'clone',
      label: _t('Clone map'),
      icon: 'clone',
      buttonLabel: _t('Clone map "%{name}"', { name: title.value }),
      run: () => emit('clone', props.map)
    })
    available.push({
      id: 'export',
      label: _t('Export map as JSON'),
      icon: 'download-json',
      buttonLabel: _t('Export map "%{name}" as JSON', { name: title.value }),
      run: () => emit('export', props.map.name)
    })
  }
  if (props.map.can_delete) {
    available.push({
      id: 'delete',
      label: _t('Delete map'),
      icon: 'delete',
      buttonLabel: _t('Delete map "%{name}"', { name: title.value }),
      run: () => emit('delete', props.map)
    })
  }
  return available
})

// Every row carries the same button, so the map has to be part of its
// accessible name for it to be tellable from the one in the next row.
const menuTitle = computed(() => _t('Actions for map "%{name}"', { name: title.value }))
</script>

<template>
  <div class="maps-map-row-actions">
    <template v-if="variant === 'inline'">
      <CmkIconButton
        v-for="action in actions"
        :key="action.id"
        class="maps-map-row-actions__button"
        :name="action.icon"
        size="small"
        :title="action.buttonLabel"
        :aria-label="action.buttonLabel"
        @click="action.run()"
      />
    </template>
    <MapsOverflowMenu v-else-if="actions.length" :label="menuTitle">
      <DropdownMenuItem
        v-for="action in actions"
        :key="action.id"
        class="maps-overflow-menu__item"
        @select="action.run()"
      >
        {{ action.label }}
      </DropdownMenuItem>
    </MapsOverflowMenu>
  </div>
</template>

<style scoped>
/* The gap the monitoring views' action cell uses, so a row of icons reads the
   same here as it does there. */
.maps-map-row-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}
</style>
