<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { fieldNumber } from '../../elements'

const { _t } = usei18n()

const props = defineProps<{ element: PresentationElement }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const aspectLocked = ref(false)

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
  <section class="maps-inspector-layout-section">
    <h3 class="maps-section-title">{{ _t('Layout') }}</h3>
    <div class="maps-inspector-layout-section__grid">
      <label class="maps-inspector-layout-section__num">
        <span class="maps-cap">{{ _t('X') }}</span>
        <CmkInput
          type="number"
          :model-value="round(element.x)"
          @update:model-value="set('x', $event)"
        />
      </label>
      <label class="maps-inspector-layout-section__num">
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
      <label class="maps-inspector-layout-section__num">
        <span class="maps-cap">{{ _t('H') }}</span>
        <CmkInput
          type="number"
          :model-value="round(element.h)"
          min="8"
          @update:model-value="setSize('h', $event)"
        />
      </label>
    </div>
    <div class="maps-inspector-layout-section__row">
      <label class="maps-inspector-layout-section__num maps-inspector-layout-section__num--rot">
        <span class="maps-cap">{{ _t('Rotation') }}</span>
        <CmkInput
          type="number"
          :model-value="Math.round(element.rotation)"
          min="-360"
          max="360"
          @update:model-value="set('rotation', $event)"
        />
      </label>
      <button
        class="maps-inspector-layout-section__aspect"
        :class="{ 'maps-inspector-layout-section__aspect--on': aspectLocked }"
        :title="_t('Lock aspect ratio')"
        @click="aspectLocked = !aspectLocked"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path v-if="aspectLocked" d="M8 11V7a4 4 0 0 1 8 0v4M5 11h14v10H5z" />
          <path v-else d="M8 11V7a4 4 0 0 1 7.5-2M5 11h14v10H5z" />
        </svg>
      </button>
    </div>
    <div class="maps-inspector-layout-section__row">
      <span class="maps-cap maps-inspector-layout-section__cap--inline">{{ _t('Opacity') }}</span>
      <input
        class="maps-range"
        type="range"
        min="0"
        max="100"
        :value="Math.round(element.opacity * 100)"
        @input="setOpacity"
      />
      <span class="maps-range-pct">{{ Math.round(element.opacity * 100) }}%</span>
    </div>
  </section>
</template>

<style scoped>
.maps-inspector-layout-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-inspector-layout-section__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.maps-inspector-layout-section__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-inspector-layout-section__num {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 0;
}

.maps-inspector-layout-section__num--rot {
  flex: 1;
}

.maps-inspector-layout-section__cap--inline {
  min-width: 52px;
}

.maps-inspector-layout-section__aspect {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-top: 14px;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
}

.maps-inspector-layout-section__aspect--on {
  color: var(--color-corporate-green-50);
  border-color: var(--color-corporate-green-50);
}

.maps-inspector-layout-section__aspect svg {
  width: 15px;
  height: 15px;
}
</style>
