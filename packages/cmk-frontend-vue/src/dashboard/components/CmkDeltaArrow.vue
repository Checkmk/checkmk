<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'

defineProps<{
  /** Which way the change went. */
  direction: 'up' | 'down'
}>()
</script>

<template>
  <!-- One triangle turned over rather than two icons, and no title: the figure
       beside it says the same thing in words, and a screen reader reading
       "triangle" over a percentage helps nobody. -->
  <CmkMultitoneIcon
    class="db-cmk-delta-arrow"
    :class="{ 'db-cmk-delta-arrow--down': direction === 'down' }"
    name="triangle-up"
    primary-color="font"
    size="xxsmall"
    :rotate="direction === 'down' ? 180 : 0"
  />
</template>

<style scoped>
.db-cmk-delta-arrow {
  flex-shrink: 0;
}
</style>
