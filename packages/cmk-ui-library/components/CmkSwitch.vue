<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'

const modelValue = defineModel({ type: Boolean, default: false })

function toggle() {
  modelValue.value = !modelValue.value
}
</script>

<template>
  <span class="cmk-switch">
    <!-- Hidden mirror: keeps native checkbox semantics for forms/v-model and
         drives the `:checked` slider styling. The visible slider is the
         interactive control. -->
    <input v-model="modelValue" type="checkbox" tabindex="-1" aria-hidden="true" />
    <span
      class="cmk-switch__slider"
      role="switch"
      tabindex="0"
      :aria-checked="modelValue"
      @click="toggle"
      @keydown.space.prevent="toggle"
      @keydown.enter.prevent="toggle"
    >
      <span class="cmk-switch__thumb">
        <CmkMultitoneIcon
          :name="modelValue ? 'checkmark' : 'cancel'"
          :primary-color="{ custom: 'var(--color-white-100)' }"
          size="xxsmall"
        />
      </span>
    </span>
  </span>
</template>

<style scoped>
/* The switch - the box around the slider */
.cmk-switch {
  position: relative;
  display: inline-block;
  width: 29px;
  height: 16px;

  /* Hide default HTML checkbox */
  input {
    opacity: 0;
    width: 0;
    height: 0;
  }
}

/* The slider */
.cmk-switch__slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  box-sizing: border-box;
  background-color: var(--switch-off-bg-color);
  border: 1px solid var(--switch-off-border-color);
  transition:
    background-color 0.4s,
    border-color 0.4s;
  border-radius: 8px; /* Rounded sliders */
}

.cmk-switch__thumb {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 12px;
  width: 12px;
  left: 1px;
  top: 1px;
  background-color: var(--switch-thumb-color);
  transition: transform 0.4s;
  border-radius: 50%; /* Rounded sliders */
}

.cmk-switch__slider:focus-visible {
  outline: revert;
}

input:checked + .cmk-switch__slider {
  background-color: var(--switch-on-bg-color);
  border-color: var(--switch-on-border-color);

  .cmk-switch__thumb {
    transform: translateX(13px);
  }
}
</style>
