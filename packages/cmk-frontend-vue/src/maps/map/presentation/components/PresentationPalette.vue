<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What can be put on a slide, and the panels that help fill it in. The monitoring
operator's primary content -- live status and text -- leads; the decorative
shapes and the image follow.
-->
<script setup lang="ts">
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import { ICONS } from '../chrome'
import { type InsertKind, insertLabel } from '../elements'
import PresentationPanel from './PresentationPanel.vue'
import PresentationToolButton from './PresentationToolButton.vue'

const { _t } = usei18n()

defineProps<{
  dataPanelOpen: boolean
  layersOpen: boolean
  /** How many data slots still have nothing bound to them. */
  unboundCount: number
}>()

const emit = defineEmits<{
  insert: [kind: InsertKind]
  connect: []
  'toggle-data-panel': []
  'toggle-layers': []
}>()

const CONTENT_TOOLS: { kind: InsertKind; icon: string }[] = [
  { kind: 'data', icon: ICONS.data },
  { kind: 'text', icon: ICONS.text }
]
const SHAPE_TOOLS: { kind: InsertKind; icon: string }[] = [
  { kind: 'rect', icon: ICONS.rect },
  { kind: 'ellipse', icon: ICONS.ellipse },
  { kind: 'line', icon: ICONS.line },
  { kind: 'arrow', icon: ICONS.arrow },
  { kind: 'image', icon: ICONS.image }
]
</script>

<template>
  <PresentationPanel class="maps-presentation-palette">
    <PresentationToolButton
      :icon="ICONS.database"
      :title="_t('Data browser')"
      :active="dataPanelOpen"
      @click="emit('toggle-data-panel')"
    />
    <div class="maps-presentation-palette__separator" />
    <PresentationToolButton
      v-for="tool in CONTENT_TOOLS"
      :key="tool.kind"
      :icon="tool.icon"
      :title="insertLabel(_t, tool.kind)"
      @click="emit('insert', tool.kind)"
    />
    <div class="maps-presentation-palette__separator" />
    <PresentationToolButton
      v-for="tool in SHAPE_TOOLS"
      :key="tool.kind"
      :icon="tool.icon"
      :title="insertLabel(_t, tool.kind)"
      @click="emit('insert', tool.kind)"
    />
    <div class="maps-presentation-palette__separator" />
    <PresentationToolButton
      :icon="ICONS.plug"
      :title="_t('Connect data')"
      :disabled="!unboundCount"
      @click="emit('connect')"
    >
      <CmkBadge
        v-if="unboundCount"
        class="maps-presentation-palette__badge"
        size="small"
        shape="circle"
      >
        {{ unboundCount }}
      </CmkBadge>
    </PresentationToolButton>
    <PresentationToolButton
      :icon="ICONS.layers"
      :title="_t('Layers')"
      :active="layersOpen"
      @click="emit('toggle-layers')"
    />
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-palette {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: var(--dimension-3);
  padding: var(--spacing-half);
  z-index: 5;
}

.maps-presentation-palette__separator {
  width: 1px;
  margin: 4px 2px;
  background: var(--default-border-color);
}

.maps-presentation-palette__badge {
  position: absolute;
  top: -4px;
  right: -4px;
}
</style>
