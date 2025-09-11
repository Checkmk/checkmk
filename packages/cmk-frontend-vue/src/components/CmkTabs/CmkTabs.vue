<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsList, TabsRoot } from 'radix-vue'

const model = defineModel<string | number>({ default: 1 })
</script>

<template>
  <TabsRoot v-model="model" orientation="horizontal" class="cmk-tabs-root">
    <TabsList as="ul" class="cmk-tabs-list">
      <slot name="tabs" />
    </TabsList>
    <slot name="tab-contents" />
  </TabsRoot>
</template>

<style scoped>
.cmk-tabs-root {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
}

.cmk-tabs-list {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: row;
  list-style-type: none;
  flex-shrink: 0;
  position: relative;
}
</style>
