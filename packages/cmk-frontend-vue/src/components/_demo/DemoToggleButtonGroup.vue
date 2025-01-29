<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

defineProps<{ screenshotMode: boolean }>()

const model = ref<string>('1')
</script>

<template>
  <ToggleButtonGroup
    v-model="model"
    :options="[
      { label: 'label1', value: '1' },
      { label: 'label2', value: '2' },
      { label: 'label3', value: '3' }
    ]"
  />

  <pre>selectedOption={{ model }}</pre>
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
