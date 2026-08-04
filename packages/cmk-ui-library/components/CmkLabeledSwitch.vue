<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

const modelValue = defineModel({ type: Boolean, default: false })

const props = defineProps<{
  offLabel: string
  onLabel: string
  offHelp?: string
  onHelp?: string
}>()

const hoveredOption = ref<'off' | 'on' | null>(null)

const hint = computed(() => {
  if (hoveredOption.value === 'off' && props.offHelp !== undefined) {
    return { label: props.offLabel, help: props.offHelp }
  }
  if (hoveredOption.value === 'on' && props.onHelp !== undefined) {
    return { label: props.onLabel, help: props.onHelp }
  }
  return null
})

function toggle() {
  modelValue.value = !modelValue.value
}
</script>

<template>
  <span class="cmk-labeled-switch">
    <span
      class="cmk-labeled-switch__control"
      role="switch"
      tabindex="0"
      :aria-checked="modelValue"
      @click="toggle"
      @keydown.space.prevent="toggle"
      @keydown.enter.prevent="toggle"
      @mouseleave="hoveredOption = null"
    >
      <span
        class="cmk-labeled-switch__option"
        :class="{ 'cmk-labeled-switch__option--active': !modelValue }"
        @mouseenter="hoveredOption = 'off'"
      >
        {{ offLabel }}
      </span>
      <span
        class="cmk-labeled-switch__option"
        :class="{ 'cmk-labeled-switch__option--active': modelValue }"
        @mouseenter="hoveredOption = 'on'"
      >
        {{ onLabel }}
      </span>
    </span>
    <!-- Pointer-only, so hidden from assistive technology: no keyboard route summons it. -->
    <span v-if="hint" class="cmk-labeled-switch__hint" aria-hidden="true">
      <b>{{ hint.label }}</b>
      <span>{{ hint.help }}</span>
    </span>
  </span>
</template>

<style scoped>
.cmk-labeled-switch {
  position: relative;
  display: inline-block;
}

/* Deliberately not CmkTooltip: graphing uses this component and does not depend on reka-ui. */
.cmk-labeled-switch__hint {
  position: absolute;
  z-index: var(--z-index-tooltip-offset);
  top: calc(100% + var(--dimension-3));
  left: 50%;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  box-sizing: border-box;
  width: max-content;
  max-width: 260px;
  padding: var(--dimension-4);
  background: var(--default-tooltip-background-color);
  border: 1px solid var(--default-tooltip-text-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-normal);
  line-height: normal;
  color: var(--default-tooltip-text-color);
  transform: translateX(-50%);
  pointer-events: none;
}

.cmk-labeled-switch__control {
  box-sizing: border-box;
  display: inline-flex;
  align-items: stretch;
  height: var(--dimension-7);
  padding: 1px;
  background-color: var(--toggle-button-group-inactive-bg-color);
  border: 1px solid var(--toggle-button-group-border-color);
  border-radius: calc(var(--dimension-7) / 2);
  cursor: pointer;

  &:focus-visible {
    outline: revert;
  }
}

.cmk-labeled-switch__option {
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  font-size: var(--font-size-normal);
  color: var(--font-color);
  border-radius: calc(var(--dimension-7) / 2);
  transition:
    background-color 0.2s,
    color 0.2s;
}

.cmk-labeled-switch__control:hover
  .cmk-labeled-switch__option:not(.cmk-labeled-switch__option--active) {
  background-color: var(--cmk-labeled-switch-hover-inactive);
}

/* The active option is green in both themes, so its label stays dark either way. */
.cmk-labeled-switch__option--active {
  background-color: var(--color-corporate-green-50);
  color: var(--color-conference-grey-100);
}

body[data-theme='facelift'] .cmk-labeled-switch {
  --cmk-labeled-switch-hover-inactive: var(--color-conference-grey-10);
}

body[data-theme='modern-dark'] .cmk-labeled-switch {
  --cmk-labeled-switch-hover-inactive: var(--color-white-10);
}
</style>
