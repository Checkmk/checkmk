<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'
</script>

<template>
  <li class="result-item-skeleton">
    <CmkSkeleton class="result-item-skeleton-handler">
      <CmkSkeleton type="icon-xlarge" class="result-item-skeleton-inner-start"></CmkSkeleton>
      <div class="result-item-skeleton-inner-end">
        <CmkSkeleton type="info-text" class="result-item-skeleton-breadcrumb"></CmkSkeleton>
        <CmkSkeleton type="text" class="result-item-skeleton-title"></CmkSkeleton>
      </div>
    </CmkSkeleton>
  </li>
</template>

<style scoped>
.result-item-skeleton {
  list-style-type: none;
  margin-bottom: var(--dimension-1) !important;
  height: 53px;

  .result-item-skeleton-handler {
    padding: var(--spacing);
    margin: 0;
    text-decoration: none;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    border: 0;
    border-radius: 0px;
    display: flex;
    flex-direction: row;
    box-sizing: border-box;
    flex: 10;
    align-items: center;
  }

  .result-item-skeleton-inner-start {
    display: flex;
    flex-direction: column;
    justify-content: center;
    margin-right: var(--spacing);
  }

  .result-item-skeleton-inner-end {
    display: flex;
    flex-direction: column;
    flex: 5;
    justify-content: center;
    align-items: flex-start;
    gap: var(--spacing-half);
  }

  .result-item-skeleton-title {
    width: 250px;
  }

  .result-item-skeleton-breadcrumb {
    width: 150px;
  }
}
</style>
