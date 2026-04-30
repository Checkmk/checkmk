<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import UclLegacyCssSwitch from './UclLegacyCssSwitch.vue'
</script>

<template>
  <div class="ucl-detail-page-component__component-container">
    <section class="ucl-detail-page-component__preview-panel" aria-label="component preview">
      <slot></slot>
    </section>
    <div class="ucl-detail-page-component__properties-panel">
      <slot name="properties"></slot>
      <UclLegacyCssSwitch></UclLegacyCssSwitch>
    </div>
  </div>
</template>

<style scoped>
.ucl-detail-page-component__component-container {
  display: flex;
  flex-wrap: wrap-reverse;
  gap: var(--dimension-10);
  padding: var(--dimension-10);
  border: 1px solid var(--ucl-elements-border-color);
  border-radius: var(--dimension-4);
  margin-top: var(--dimension-8);
}

.ucl-detail-page-component__preview-panel {
  flex: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-10);
}

.ucl-detail-page-component__properties-panel {
  flex: 1 0 300px;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
