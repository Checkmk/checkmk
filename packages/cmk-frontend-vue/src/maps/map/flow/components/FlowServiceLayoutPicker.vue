<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Which of a host's services a flow map draws, and in what shape.

The choice belongs on the map rather than in its settings, because it is how an
operator reads the map: off for the shape of the network, a ring for how each
host is doing, a fan or an orbit or a grid to see the services themselves. It
also decides how much the backend has to send, so it is the one switch that
changes what a large map costs to look at.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import MapOverlayButton from '@/maps/map/components/MapOverlayButton.vue'
import type { ServiceLayout } from '@/maps/types/api'

const { _t } = usei18n()

const props = defineProps<{
  modelValue: ServiceLayout
  /** The shapes on offer, where the map cannot draw them all. */
  layouts?: ServiceLayout[] | undefined
}>()
const emit = defineEmits<{ 'update:modelValue': [layout: ServiceLayout] }>()

const open = ref(false)

const labels = computed<Record<ServiceLayout, string>>(() => ({
  off: _t('Off'),
  donut: _t('Donut'),
  fan: _t('Fan'),
  orbit: _t('Orbit'),
  row: _t('Row')
}))

const ORDER: ServiceLayout[] = ['off', 'donut', 'fan', 'orbit', 'row']

const options = computed(() =>
  ORDER.filter((value) => !props.layouts || props.layouts.includes(value)).map((value) => ({
    value,
    label: labels.value[value]
  }))
)

const shown = computed(() => labels.value[props.modelValue])

function pick(layout: ServiceLayout): void {
  emit('update:modelValue', layout)
  open.value = false
}
</script>

<template>
  <div class="maps-flow-service-layout-picker" @keydown.escape="open = false">
    <!-- Pointer-only dismissal; Escape above is the keyboard path, so this
         stays out of the accessibility tree. -->
    <div
      v-if="open"
      class="maps-flow-service-layout-picker__backdrop"
      aria-hidden="true"
      @click="open = false"
    />

    <MapOverlayButton
      class="maps-flow-service-layout-picker__button"
      :expanded="open"
      aria-haspopup="menu"
      @click="open = !open"
    >
      {{ _t('Services: %{layout}', { layout: shown }) }}
    </MapOverlayButton>

    <Transition
      enter-from-class="maps-flow-service-layout-picker__menu-enter-from"
      enter-active-class="maps-flow-service-layout-picker__menu-enter-active"
      leave-to-class="maps-flow-service-layout-picker__menu-leave-to"
      leave-active-class="maps-flow-service-layout-picker__menu-leave-active"
    >
      <div
        v-if="open"
        class="maps-flow-service-layout-picker__menu"
        role="menu"
        :aria-label="_t('Services')"
      >
        <button
          v-for="option in options"
          :key="option.value"
          role="menuitemradio"
          :aria-checked="props.modelValue === option.value"
          class="maps-flow-service-layout-picker__item"
          :class="
            props.modelValue === option.value ? 'maps-flow-service-layout-picker__item--active' : ''
          "
          @click="pick(option.value)"
        >
          {{ option.label }}
          <CmkIcon v-if="props.modelValue === option.value" name="checkmark" size="small" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.maps-flow-service-layout-picker {
  position: relative;
}

.maps-flow-service-layout-picker__backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
}

/* As high as the legend button beside it. */
.maps-flow-service-layout-picker__button {
  position: relative;
  z-index: 10;
  padding: var(--dimension-3) var(--dimension-5);
  line-height: 16px;
  box-shadow: var(--maps-shadow-canvas-overlay-high);
}

.maps-flow-service-layout-picker__button:focus-visible {
  outline: revert;
}

.maps-flow-service-layout-picker__menu {
  position: absolute;
  right: 0;
  bottom: 100%;
  left: 0;
  z-index: 10;
  margin-bottom: var(--dimension-4);
  overflow: hidden;
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    var(--maps-shadow-canvas-overlay-high);
}

.maps-flow-service-layout-picker__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--dimension-3) var(--dimension-5);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  line-height: 16px;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.maps-flow-service-layout-picker__item:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-flow-service-layout-picker__item--active,
.maps-flow-service-layout-picker__item--active:hover {
  color: var(--interactive-accent-subtle);
  background: color-mix(in srgb, var(--interactive-accent) 10%, transparent);
}

.maps-flow-service-layout-picker__menu-enter-from,
.maps-flow-service-layout-picker__menu-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.maps-flow-service-layout-picker__menu-enter-active {
  transform-origin: bottom right;
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
}

.maps-flow-service-layout-picker__menu-leave-active {
  transform-origin: bottom right;
  transition: all 0.1s cubic-bezier(0.4, 0, 1, 1);
}
</style>
