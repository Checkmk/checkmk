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
    <h3>Default (open)</h3>
    <CmkCatalogPanel :title="'Default Panel'">This panel is open by default</CmkCatalogPanel>

    <h3>Explicitly closed</h3>
    <CmkCatalogPanel :title="'Closed Panel'" :open="false">
      This panel is closed by default
    </CmkCatalogPanel>

    <h3>With custom header slot</h3>
    <CmkCatalogPanel :title="'Custom Header'">
      <template #header>
        <i>Some custom header</i>
      </template>
      Custom content with styled header
    </CmkCatalogPanel>

    <h3>Closed with custom header</h3>
    <CmkCatalogPanel :title="'Closed with Custom'" :open="false">
      <template #header>
        <b>Bold custom header</b>
      </template>
      This panel starts closed with custom header styling
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
