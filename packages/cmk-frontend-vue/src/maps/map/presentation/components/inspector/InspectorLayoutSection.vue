<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { fieldNumber } from '../../elements'

const { _t } = usei18n()

const props = defineProps<{ element: PresentationElement }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const aspectLocked = ref(false)
const aspectLabel = computed(() =>
  aspectLocked.value ? _t('Unlock aspect ratio') : _t('Lock aspect ratio')
)

function round(v: number): number {
  return Math.round(v)
}

function set(key: 'x' | 'y' | 'rotation', value: unknown): void {
  const v = fieldNumber(value)
  if (v === null) {
    return
  }
  emit('patch', { [key]: v })
}

// With the aspect lock on, editing one dimension scales the other to keep the
// element's current ratio — the staple a designer expects from W/H fields.
function setSize(key: 'w' | 'h', value: unknown): void {
  const v = fieldNumber(value)
  if (v === null || v < 8) {
    return
  }
  if (!aspectLocked.value || props.element.w <= 0 || props.element.h <= 0) {
    emit('patch', { [key]: v })
    return
  }
  const ratio = props.element.w / props.element.h
  if (key === 'w') {
    emit('patch', { w: v, h: Math.max(8, Math.round(v / ratio)) })
  } else {
    emit('patch', { h: v, w: Math.max(8, Math.round(v * ratio)) })
  }
}

function setOpacity(e: Event): void {
  emit('patch', { opacity: Number((e.target as HTMLInputElement).value) / 100 })
}
</script>

<template>
  <CmkCatalogPanel :title="_t('Layout')">
    <div class="maps-inspector-layout-section">
      <div class="maps-inspector-layout-section__grid">
        <label class="maps-inspector-layout-section__num">
          <span class="maps-cap">{{ _t('X') }}</span>
          <CmkInput
            type="number"
            :model-value="round(element.x)"
            @update:model-value="set('x', $event)"
          />
        </label>
        <label
          class="maps-inspector-layout-section__num maps-inspector-layout-section__num--second"
        >
          <span class="maps-cap">{{ _t('Y') }}</span>
          <CmkInput
            type="number"
            :model-value="round(element.y)"
            @update:model-value="set('y', $event)"
          />
        </label>
        <label class="maps-inspector-layout-section__num">
          <span class="maps-cap">{{ _t('W') }}</span>
          <CmkInput
            type="number"
            :model-value="round(element.w)"
            min="8"
            @update:model-value="setSize('w', $event)"
          />
        </label>
        <button
          type="button"
          class="maps-inspector-layout-section__aspect"
          :class="{ 'maps-inspector-layout-section__aspect--on': aspectLocked }"
          :title="aspectLabel"
          :aria-label="aspectLabel"
          :aria-pressed="aspectLocked"
          @click="aspectLocked = !aspectLocked"
        >
          <CmkMultitoneIcon
            :name="aspectLocked ? 'chain' : 'broken-chain'"
            primary-color="font"
            size="small"
          />
        </button>
        <label class="maps-inspector-layout-section__num">
          <span class="maps-cap">{{ _t('H') }}</span>
          <CmkInput
            type="number"
            :model-value="round(element.h)"
            min="8"
            @update:model-value="setSize('h', $event)"
          />
        </label>
        <label class="maps-inspector-layout-section__num">
          <span class="maps-cap">{{ _t('Rotation') }}</span>
          <CmkInput
            type="number"
            :model-value="Math.round(element.rotation)"
            min="-360"
            max="360"
            @update:model-value="set('rotation', $event)"
          />
        </label>
      </div>
      <div class="maps-inspector-layout-section__field">
        <span class="maps-cap">{{ _t('Opacity') }}</span>
        <div class="maps-inspector-layout-section__row">
          <input
            class="maps-inspector-layout-section__range"
            type="range"
            min="0"
            max="100"
            :aria-label="_t('Opacity')"
            :value="Math.round(element.opacity * 100)"
            @input="setOpacity"
          />
          <span class="maps-range-pct">{{ Math.round(element.opacity * 100) }}%</span>
        </div>
      </div>
    </div>
  </CmkCatalogPanel>
</template>

<style scoped>
.maps-inspector-layout-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-4) 0;
}

/* X/Y and W/H line up in two columns; the aspect lock sits between W and H. */
.maps-inspector-layout-section__grid {
  display: grid;
  grid-template-columns: max-content max-content max-content;
  gap: var(--dimension-5) var(--dimension-4);
  align-items: end;
}

.maps-inspector-layout-section__num {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-inspector-layout-section__num--second {
  grid-column: 3;
}

.maps-inspector-layout-section__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-inspector-layout-section__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-inspector-layout-section__range {
  flex: 1;
  min-width: 0;
}

.maps-inspector-layout-section__aspect {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin: 0;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  background: transparent;
  cursor: pointer;
  opacity: 0.6;
}

.maps-inspector-layout-section__aspect:hover {
  opacity: 1;
}

.maps-inspector-layout-section__aspect--on {
  border-color: var(--interactive-accent);
  opacity: 1;
}
</style>
