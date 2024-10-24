<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
const data = defineModel('data', { type: String, default: '#ff0000' })
</script>

<template>
  <input id="color-picker" v-model="data" type="color" />
</template>

<style scoped>
#color-picker {
  margin-right: 10px;
  width: 26px;
  height: 30px;
  padding: 0;
  border: none;
  background: transparent;
}
</style>
