<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <div class="demo-cmk-catalog-panel__container">
    <CmkCatalogPanel :title="'foo'">bar</CmkCatalogPanel>
    <CmkCatalogPanel :title="'foo'">
      <template #header>
        <i>Some custom header</i>
      </template>
      bar
    </CmkCatalogPanel>
  </div>
</template>

<style scoped>
.demo-cmk-catalog-panel__container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
