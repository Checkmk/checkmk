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

import type { ServiceLayout } from '@/maps/types/api'

const { _t } = usei18n()

const props = defineProps<{ modelValue: ServiceLayout }>()
const emit = defineEmits<{ 'update:modelValue': [layout: ServiceLayout] }>()

const open = ref(false)

const options = computed<{ value: ServiceLayout; label: string }[]>(() => [
  { value: 'off', label: _t('Off') },
  { value: 'donut', label: _t('Donut') },
  { value: 'fan', label: _t('Fan') },
  { value: 'orbit', label: _t('Orbit') },
  { value: 'row', label: _t('Row') }
])

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

    <button
      class="maps-flow-service-layout-picker__button"
      :class="
        props.modelValue !== 'off'
          ? 'maps-flow-service-layout-picker__button--on'
          : 'maps-flow-service-layout-picker__button--off'
      "
      :aria-expanded="open"
      aria-haspopup="menu"
      @click="open = !open"
    >
      {{ _t('Services') }}
      <svg
        class="maps-flow-service-layout-picker__caret"
        :class="open ? 'maps-flow-service-layout-picker__caret--open' : ''"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    </button>

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
  position: absolute;
  right: var(--dimension-8);
  bottom: var(--dimension-8);
  z-index: 40;
}

.maps-flow-service-layout-picker__backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.maps-flow-service-layout-picker__button {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
  padding: var(--spacing-half) var(--spacing);
  font-size: var(--font-size-normal);
  font-weight: 500;
  line-height: 16px;
  border-radius: 12px;
  transition: all 0.2s;
}

.maps-flow-service-layout-picker__button--on {
  color: var(--color-corporate-green-40);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.maps-flow-service-layout-picker__button--off {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--ux-theme-3) 80%, transparent);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.maps-flow-service-layout-picker__button--off:hover {
  color: var(--font-color);
  background: var(--ux-theme-3);
}

.maps-flow-service-layout-picker__caret {
  width: 10px;
  height: 10px;
  transition: transform 0.15s;
}

.maps-flow-service-layout-picker__caret--open {
  transform: rotate(180deg);
}

.maps-flow-service-layout-picker__menu {
  position: absolute;
  right: 0;
  bottom: 100%;
  z-index: 10;
  width: 120px;
  margin-bottom: 6px;
  overflow: hidden;
  background: var(--ux-theme-3);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 50%);
}

.maps-flow-service-layout-picker__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--spacing-half) var(--spacing);
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
  color: var(--color-corporate-green-40);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
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
