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

The glyphs are the ones Checkmk shows for the same actions everywhere else,
drawn colourless: several of them are multi-coloured, which side by side read
as a row of unrelated pictures rather than as one set of actions.
-->
<script setup lang="ts">
import type { IconNames } from 'cmk-shared-typing/typescript/icon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import type { MapElement } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { useAnchorOverlayStyle } from '@/maps/utils/overlayFrame'

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
  /** The selected object on screen, which the toolbar sits above. */
  anchor: AnchorRect
  selectedCount: number
  /** Several hosts at one place can be merged into a single location icon. */
  canBundle: boolean
  isBundle: boolean
}>()

const emit = defineEmits<{ act: [action: MapObjectAction] }>()

const { _t, _tn } = usei18n()

const barEl = ref<HTMLElement | null>(null)
const barStyle = useAnchorOverlayStyle(barEl, () => props.anchor)

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
  <div ref="barEl" class="maps-map-object-action-bar" :style="barStyle">
    <span class="maps-map-object-action-bar__label">{{ label }}</span>
    <span class="maps-map-object-action-bar__divider" />
    <template v-for="button in buttons" :key="button.action">
      <!-- Set apart: the one action that cannot be undone. -->
      <span v-if="button.tone === 'danger'" class="maps-map-object-action-bar__divider" />
      <CmkIconButton
        class="maps-map-object-action-bar__button"
        :class="button.tone ? `maps-map-object-action-bar__button--${button.tone}` : ''"
        :name="button.icon"
        :colored="false"
        size="medium"
        :title="button.title"
        :aria-label="button.title"
        @click="emit('act', button.action)"
      />
    </template>
  </div>
</template>

<style scoped>
.maps-map-object-action-bar {
  position: fixed;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-3) 6px;
  background: var(--ux-theme-3);
  border-radius: var(--dimension-5);
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
  margin: 0 1px;
  background: var(--ux-theme-5);
}

/* Doubled to outweigh CmkIconButton's own padding reset. */
.maps-map-object-action-bar__button.maps-map-object-action-bar__button {
  padding: 7px;
  border-radius: var(--dimension-4);
  transition: background-color 0.15s;
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
