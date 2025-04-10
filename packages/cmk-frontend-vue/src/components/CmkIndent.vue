<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const { indent = true } = defineProps<{
  indent?: boolean
}>()

const LINE_OVERHANG = '5px'
</script>

<template>
  <div :class="{ 'cmk-indent': indent }">
    <slot />
  </div>
</template>

<style scoped>
.cmk-indent {
  --line-overhang: v-bind(LINE_OVERHANG);
  float: none;
  margin-left: 6px;
  padding-top: var(--line-overhang);
  padding-bottom: var(--line-overhang);
  margin-top: calc(var(--spacing) - var(--line-overhang));
  margin-bottom: calc(var(--spacing) - var(--line-overhang));
  padding-left: var(--spacing);
  border-left: 2px solid var(--ux-theme-5);
}

.cmk-indent:empty {
  margin: 0;
  padding: 0;
}
</style>
