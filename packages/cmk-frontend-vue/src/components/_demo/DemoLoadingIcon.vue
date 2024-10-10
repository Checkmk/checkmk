<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import LoadingIcon from '@/components/LoadingIcon.vue'
</script>

<template>
  <ul>
    <li>xl: <LoadingIcon size="xl" /></li>
    <li>lg: <LoadingIcon size="lg" /></li>
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
