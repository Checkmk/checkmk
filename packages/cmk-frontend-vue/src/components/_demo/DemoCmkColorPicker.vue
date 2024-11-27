<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkColorPicker from '@/components/CmkColorPicker.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const data = ref('#ff0000')
</script>

<template>
  <ul>
    <li><CmkColorPicker v-model:data="data"></CmkColorPicker></li>
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
