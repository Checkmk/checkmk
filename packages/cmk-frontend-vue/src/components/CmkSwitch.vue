<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
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
    ></span>
  </span>
</template>

<style scoped>
/* The switch - the box around the slider */
.cmk-switch {
  position: relative;
  display: inline-block;
  width: 18px;
  height: 10px;

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
  background-color: var(--color-daylight-grey-60);
  transition: background-color 0.4s;
  border-radius: 5px; /* Rounded sliders */

  &::before {
    position: absolute;
    content: '';
    height: 8px;
    width: 8px;
    left: 1px;
    bottom: 1px;
    background-color: white;
    transition: transform 0.4s;
    border-radius: 50%; /* Rounded sliders */
  }
}

.cmk-switch__slider:focus-visible {
  outline: revert;
}

input:checked + .cmk-switch__slider {
  background-color: var(--color-corporate-green-50);

  &::before {
    transform: translateX(8px);
  }
}
</style>
