<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import IconButton from '@/components/IconButton.vue'
</script>

<template>
  <ul>
    <li><IconButton label="some label" icon-name="continue" variant="custom" /></li>
    <li><IconButton label="next label" variant="next" /></li>
    <li><IconButton label="prev label" variant="prev" /></li>
    <li><IconButton label="save label" variant="save" /></li>
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
