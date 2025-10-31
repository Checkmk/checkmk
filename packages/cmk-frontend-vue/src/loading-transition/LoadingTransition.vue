<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type LoadingTransition } from 'cmk-shared-typing/typescript/loading_transition'

import CmkSkeleton from '@/components/CmkSkeleton.vue'

import CatalogSkeleton from './CatalogSkeleton.vue'
import TableSkeleton from './TableSkeleton.vue'

defineProps<{
  template: LoadingTransition
}>()
</script>

<template>
  <div class="loading-transition__container">
    <div class="loading-transition__titlebar">
      <CmkSkeleton type="h1" :width="'400px'" class="loading-transition__skel-title" />
      <span class="loading-transition__skel-breadcrumbs">
        <CmkSkeleton type="text" /> > <CmkSkeleton type="text" /> >
        <CmkSkeleton type="text" :width="'100px'" />
      </span>
    </div>
    <div class="loading-transition__page-menu-bar">
      <CmkSkeleton type="text" :width="'80px'" class="loading-transition__bar-element" />
      <CmkSkeleton type="text" class="loading-transition__bar-element" />
      <CmkSkeleton type="text" :width="'100px'" class="loading-transition__bar-element" />
    </div>
    <TableSkeleton v-if="template === 'table'" />
    <CatalogSkeleton v-else-if="template === 'catalog'" />
  </div>
</template>

<style scoped>
.loading-transition__container {
  max-height: 100%;
  overflow-y: hidden;
  pointer-events: none;
}

.loading-transition__titlebar {
  display: flex;
  flex-direction: column;
  height: 53px;
  padding: 5px 10px 0;
  color: var(--font-color-dimmed);
}

.loading-transition__skel-title {
  background: var(--ux-theme-4);
  margin-top: 6px;
}

.loading-transition__skel-breadcrumbs {
  margin-top: 3px;
}

.loading-transition__page-menu-bar {
  display: flex;
  align-items: center;
  width: 100%;
  height: 27px;
  background: var(--ux-theme-0);
  margin-bottom: 10px;

  > .loading-transition__bar-element {
    background: var(--ux-theme-5);
    margin: 2px 10px;
  }
}
</style>
