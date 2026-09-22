<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Everything on the slide, front to back: what it is called, whether it is
locked or hidden, and whether it still needs data connected. It is a tool panel
rather than a dropdown -- it stays open across canvas and inspector work
(multi-step cleanups) until it is closed or re-toggled.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { isUnboundSlot } from '../binding'
import { ICONS } from '../chrome'
import { elementLabel } from '../elements'
import PresentationGlyph from './PresentationGlyph.vue'
import PresentationPanel from './PresentationPanel.vue'

const { _t } = usei18n()

const props = defineProps<{
  /** Top-level elements only — a group stands in for its members. */
  elements: PresentationElement[]
  selectedIds: string[]
}>()

const emit = defineEmits<{
  /** ``extend`` means shift/ctrl/cmd was held: add to or remove from the selection. */
  pick: [id: string, extend: boolean]
  'toggle-lock': [id: string]
  'toggle-hidden': [id: string]
  group: []
  ungroup: []
  close: []
}>()

const canGroup = computed(() => props.selectedIds.length >= 2)
const canUngroup = computed(() =>
  props.elements.some((el) => el.kind === 'group' && props.selectedIds.includes(el.id))
)

function onRowClick(id: string, e: MouseEvent): void {
  emit('pick', id, e.shiftKey || e.ctrlKey || e.metaKey)
}
</script>

<template>
  <PresentationPanel raised class="maps-presentation-layers-panel" @pointerdown.stop>
    <div class="maps-presentation-layers-panel__head">
      <span>{{ _t('Layers') }}</span>
      <CmkIconButton
        name="close"
        size="small"
        :title="_t('Close')"
        :aria-label="_t('Close')"
        @click="emit('close')"
      />
    </div>
    <div class="maps-presentation-layers-panel__hint">
      {{ _t('Shift-click to select multiple') }}
    </div>
    <div
      v-for="el in elements"
      :key="el.id"
      class="maps-presentation-layers-panel__row"
      :class="{
        'maps-presentation-layers-panel__row--selected': selectedIds.includes(el.id),
        'maps-presentation-layers-panel__row--hidden': el.hidden
      }"
      @click="onRowClick(el.id, $event)"
    >
      <span class="maps-presentation-layers-panel__name">{{ elementLabel(_t, el) }}</span>
      <span
        v-if="isUnboundSlot(el)"
        class="maps-presentation-layers-panel__unbound"
        :title="_t('Not connected')"
      />
      <button
        class="maps-presentation-layers-panel__toggle"
        :class="{ 'maps-presentation-layers-panel__toggle--on': el.locked }"
        :title="el.locked ? _t('Unlock') : _t('Lock')"
        :aria-pressed="el.locked"
        @click.stop="emit('toggle-lock', el.id)"
      >
        <PresentationGlyph :svg="el.locked ? ICONS.lock : ICONS.unlock" />
      </button>
      <button
        class="maps-presentation-layers-panel__toggle"
        :class="{ 'maps-presentation-layers-panel__toggle--on': el.hidden }"
        :title="el.hidden ? _t('Show') : _t('Hide')"
        :aria-pressed="el.hidden"
        @click.stop="emit('toggle-hidden', el.id)"
      >
        <PresentationGlyph :svg="el.hidden ? ICONS.eyeOff : ICONS.eye" />
      </button>
    </div>
    <div class="maps-presentation-layers-panel__foot">
      <CmkButton variant="optional" size="small" :disabled="!canGroup" @click="emit('group')">
        {{ _t('Group') }}
      </CmkButton>
      <CmkButton variant="optional" size="small" :disabled="!canUngroup" @click="emit('ungroup')">
        {{ _t('Ungroup') }}
      </CmkButton>
    </div>
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-layers-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 224px;
  max-height: 70%;
  overflow: auto;
  color: var(--font-color);
  z-index: 6;
  animation: maps-presentation-layers-panel-pop 0.12s ease-out;
}

@keyframes maps-presentation-layers-panel-pop {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-presentation-layers-panel {
    animation: none;
  }
}

.maps-presentation-layers-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  font-weight: var(--font-weight-bold);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-presentation-layers-panel__hint {
  padding: 6px 10px 4px;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-presentation-layers-panel__row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
}

.maps-presentation-layers-panel__row:hover {
  background: var(--input-hover-bg-color);
}

.maps-presentation-layers-panel__row--selected {
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
}

.maps-presentation-layers-panel__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-normal);
}

.maps-presentation-layers-panel__row--hidden .maps-presentation-layers-panel__name {
  opacity: 0.5;
  font-style: italic;
}

.maps-presentation-layers-panel__unbound {
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border: 1.5px dashed var(--color-corporate-green-50);
  border-radius: 9999px;
}

.maps-presentation-layers-panel__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.maps-presentation-layers-panel__toggle :deep(svg) {
  width: 15px;
  height: 15px;
}

.maps-presentation-layers-panel__toggle:hover {
  background: var(--input-hover-bg-color);
  color: var(--font-color);
}

.maps-presentation-layers-panel__toggle--on {
  color: var(--color-corporate-green-50);
}

.maps-presentation-layers-panel__foot {
  display: flex;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid var(--default-border-color);
}
</style>
