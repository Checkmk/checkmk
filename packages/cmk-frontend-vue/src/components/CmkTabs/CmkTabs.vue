<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsIndicator, TabsList, TabsRoot } from 'radix-vue'

const model = defineModel<string | number>({ default: 1 })
</script>

<template>
  <TabsRoot v-model="model" orientation="horizontal" class="cmk-tabs-root">
    <TabsList as="ul" class="cmk-tabs-list">
      <TabsIndicator class="cmk-tags-indicator">
        <div style="width: 100%; height: 100%" class="cmk-tags-indicator-highlight" />
      </TabsIndicator>
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
  background: var(--default-bg-color);
}

.cmk-tabs-list {
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: row;
  list-style-type: none;
  flex-shrink: 0;
  border-bottom: 1px solid var(--default-border-color);
  position: relative;
}

.cmk-tags-indicator {
  position: absolute;
  left: 0;
  height: 2px;
  top: 0;
  width: var(--radix-tabs-indicator-size);
  transform: translateX(var(--radix-tabs-indicator-position));
  transition-property: width, transform;
  transition-duration: 300ms;
  z-index: +1;
}

.cmk-tags-indicator-highlight {
  width: 100%;
  height: 100%;
  background: var(--success);
}
</style>
