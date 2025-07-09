<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <ul class="result-list">
    <slot />
  </ul>
</template>

<style scoped>
.result-list {
  padding: 0;
  margin: 0;
  list-style-type: 0;
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
