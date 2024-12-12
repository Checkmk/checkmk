<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
const data = defineModel('data', { type: Boolean, default: false })
</script>

<template>
  <label class="cmk-switch">
    <input v-model="data" type="checkbox" />
    <span class="cmk-switch__slider"></span>
  </label>
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  -webkit-transition: 0.4s;
  transition: 0.4s;
  border-radius: 5px; /* Rounded sliders */

  &:before {
    position: absolute;
    content: '';
    height: 8px;
    width: 8px;
    left: 1px;
    bottom: 1px;
    background-color: white;
    -webkit-transition: 0.4s;
    transition: 0.4s;
    border-radius: 50%; /* Rounded sliders */
  }
}

input:checked + .cmk-switch__slider {
  background-color: #13d389;

  &:before {
    -webkit-transform: translateX(8px);
    -ms-transform: translateX(8px);
    transform: translateX(8px);
  }
}

input:focus + .cmk-switch__slider {
  box-shadow: 0 0 1px #2196f3;
}
</style>
