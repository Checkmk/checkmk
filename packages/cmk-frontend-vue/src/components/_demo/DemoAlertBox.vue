<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import AlertBox from '@/components/AlertBox.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <ul>
    <li><AlertBox variant="success">success</AlertBox></li>
    <li><AlertBox variant="info">info</AlertBox></li>
    <li><AlertBox variant="warning">warning</AlertBox></li>
    <li><AlertBox variant="error">error</AlertBox></li>
  </ul>
</template>

<style scoped>
ul {
  list-style-type: none;
  padding: 0;
}
li {
  margin: 1em;
}
</style>
