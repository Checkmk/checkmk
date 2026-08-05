<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
const modelValue = defineModel({ type: Boolean, default: false })

defineProps<{
  offLabel: string
  onLabel: string
}>()

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
    >
      <span
        class="cmk-labeled-switch__option"
        :class="{ 'cmk-labeled-switch__option--active': !modelValue }"
      >
        {{ offLabel }}
      </span>
      <span
        class="cmk-labeled-switch__option"
        :class="{ 'cmk-labeled-switch__option--active': modelValue }"
      >
        {{ onLabel }}
      </span>
    </span>
  </span>
</template>

<style scoped>
.cmk-labeled-switch {
  display: inline-block;
}

.cmk-labeled-switch__control {
  box-sizing: border-box;
  display: inline-flex;
  align-items: stretch;
  height: var(--dimension-7);
  padding: 1px;
  background-color: var(--color-midnight-grey-100);
  border: 1px solid var(--color-mid-grey-60);
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
  font-size: var(--font-size-small);
  color: var(--color-white-100);
  border-radius: calc(var(--dimension-7) / 2);
  transition:
    background-color 0.2s,
    color 0.2s;
}

.cmk-labeled-switch__control:hover
  .cmk-labeled-switch__option:not(.cmk-labeled-switch__option--active) {
  background-color: var(--color-white-10);
}

.cmk-labeled-switch__option--active {
  background-color: var(--color-corporate-green-50);
  color: var(--color-conference-grey-100);
}
</style>
