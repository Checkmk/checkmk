<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What can be done to the object under the cursor, right next to it: edit,
duplicate, restack, bundle, delete.

A toolbar beside the selection rather than a menu somewhere else — while
arranging a map, the operator's attention is on the object, and the actions
have to be one click away from it.

The glyphs are drawn colourless: several of them are Checkmk's own
multi-coloured icons, which side by side read as a row of unrelated pictures
rather than as one set of actions.
-->
<script setup lang="ts">
import type { IconNames } from 'cmk-shared-typing/typescript/icon'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { MapElement } from '@/maps/types/api'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'

/** What the toolbar can ask the view to do with the selection. */
export type MapObjectAction =
  | 'edit'
  | 'duplicate'
  | 'detach'
  | 'front'
  | 'back'
  | 'bundle'
  | 'unbundle'
  | 'delete'

const props = defineProps<{
  object: MapElement
  selectedCount: number
  /** Several hosts at one place can be merged into a single location icon. */
  canBundle: boolean
  isBundle: boolean
}>()

const emit = defineEmits<{ act: [action: MapObjectAction] }>()

const { _t, _tn } = usei18n()

const isSingle = computed(() => props.selectedCount <= 1)
/** A line bound to an object follows it, and can be freed again. */
const isAttachedLine = computed(
  () => props.object.type === 'line' && !!(props.object.start_ref || props.object.end_ref)
)

const label = computed<TranslatedString>(() =>
  isSingle.value
    ? objectTypeLabel(props.object.type, _t)
    : _tn('%{n} selected', '%{n} selected', props.selectedCount, { n: props.selectedCount })
)

interface ActionButton {
  action: MapObjectAction
  icon: IconNames
  title: TranslatedString
  tone?: 'edit' | 'danger'
}

const buttons = computed<ActionButton[]>(() => {
  const available: ActionButton[] = []
  if (isSingle.value) {
    available.push(
      { action: 'edit', icon: 'edit', title: _t('Edit properties'), tone: 'edit' },
      { action: 'duplicate', icon: 'clone', title: _t('Duplicate') }
    )
    if (isAttachedLine.value) {
      available.push({
        action: 'detach',
        icon: 'dissolve-operation',
        title: _t('Detach from object')
      })
    }
  }
  available.push(
    { action: 'front', icon: 'top', title: _t('Bring to front') },
    { action: 'back', icon: 'bottom', title: _t('Send to back') }
  )
  if (props.canBundle) {
    available.push({ action: 'bundle', icon: 'aggr', title: _t('Bundle into a location') })
  }
  if (props.isBundle) {
    available.push({ action: 'unbundle', icon: 'dissolve-operation', title: _t('Unbundle') })
  }
  available.push({
    action: 'delete',
    icon: 'delete',
    title: isSingle.value ? _t('Delete') : _t('Delete selected'),
    tone: 'danger'
  })
  return available
})
</script>

<template>
  <div class="maps-map-object-action-bar">
    <span class="maps-map-object-action-bar__label">{{ label }}</span>
    <span class="maps-map-object-action-bar__divider" />
    <button
      v-for="button in buttons"
      :key="button.action"
      type="button"
      class="maps-map-object-action-bar__button"
      :class="button.tone ? `maps-map-object-action-bar__button--${button.tone}` : ''"
      :title="button.title"
      :aria-label="button.title"
      @click="emit('act', button.action)"
    >
      <CmkIcon :name="button.icon" size="small" :colored="false" />
    </button>
  </div>
</template>

<style scoped>
.maps-map-object-action-bar {
  position: fixed;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  padding: var(--dimension-3);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 40%);
}

.maps-map-object-action-bar__label {
  padding: 0 var(--dimension-3);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
}

.maps-map-object-action-bar__divider {
  width: 1px;
  height: 14px;
  background: var(--default-border-color);
}

.maps-map-object-action-bar__button {
  display: flex;
  align-items: center;
  padding: var(--dimension-3);
  border-radius: var(--border-radius-half);
}

.maps-map-object-action-bar__button:hover {
  background: var(--input-hover-bg-color);
}

.maps-map-object-action-bar__button--edit:hover {
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.maps-map-object-action-bar__button--danger:hover {
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}
</style>
