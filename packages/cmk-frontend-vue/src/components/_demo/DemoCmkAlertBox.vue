<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from '@/components/CmkAlertBox.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <ul>
    <li><CmkAlertBox variant="success">success</CmkAlertBox></li>
    <li><CmkAlertBox variant="info">info</CmkAlertBox></li>
    <li><CmkAlertBox variant="warning">warning</CmkAlertBox></li>
    <li><CmkAlertBox variant="error">error</CmkAlertBox></li>
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
