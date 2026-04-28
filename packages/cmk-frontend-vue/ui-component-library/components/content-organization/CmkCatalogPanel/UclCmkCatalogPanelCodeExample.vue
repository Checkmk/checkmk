<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
</script>

<template>
  <CmkCatalogPanel title="Catalog Panel" variant="default" :open="true">
    This is the collapsible content inside the panel.
  </CmkCatalogPanel>
</template>
