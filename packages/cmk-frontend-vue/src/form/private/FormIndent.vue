<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const { indent = true } = defineProps<{
  indent?: boolean
}>()
</script>

<template>
  <div :class="{ 'form-indent': indent }">
    <slot />
  </div>
</template>

<style scoped>
.form-indent {
  float: none;
  margin-top: 3px;
  margin-bottom: 10px;
  margin-left: 6px;
  padding-left: 10px;
  border-left: 2px solid var(--ux-theme-5);
}

.form-indent:empty {
  margin: 0;
}
</style>
