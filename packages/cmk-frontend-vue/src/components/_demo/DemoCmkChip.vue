<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkChip from '../CmkChip.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <h2>Small</h2>
  <CmkChip size="small" content="1"></CmkChip>
  <CmkChip size="small" content="some long content"></CmkChip>
  <h2>Medium</h2>
  <CmkChip content="1"></CmkChip>
  <CmkChip content="some long content"></CmkChip>
  <h2>Large</h2>
  <CmkChip size="large" content="1"></CmkChip>
  <CmkChip size="large" content="some long content"></CmkChip>
</template>

<style scoped>
h2 {
  margin: 16px 0;
}
</style>
