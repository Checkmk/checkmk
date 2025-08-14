<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <div>
    <CmkKeyboardKey size="small" keyboard-key="Ctrl"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="arrow-left"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="arrow-right"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="arrow-up"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="arrow-down"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="enter"></CmkKeyboardKey>
    <CmkKeyboardKey size="small" keyboard-key="backspace"></CmkKeyboardKey>
  </div>
  <div>
    <CmkKeyboardKey keyboard-key="Ctrl"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="arrow-left"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="arrow-right"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="arrow-up"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="arrow-down"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="enter"></CmkKeyboardKey>
    <CmkKeyboardKey keyboard-key="backspace"></CmkKeyboardKey>
  </div>
  <div>
    <CmkKeyboardKey size="large" keyboard-key="Ctrl"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="arrow-left"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="arrow-right"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="arrow-up"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="arrow-down"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="enter"></CmkKeyboardKey>
    <CmkKeyboardKey size="large" keyboard-key="backspace"></CmkKeyboardKey>
  </div>
</template>

<style scoped>
div {
  margin-bottom: 10px;
}
</style>
