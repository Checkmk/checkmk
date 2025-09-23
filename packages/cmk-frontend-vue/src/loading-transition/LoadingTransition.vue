<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

// Enable once dynamic behavior is needed
// const props = defineProps<{
//   template: string
// }>()
</script>

<template>
  <CmkSkeleton type="box" class="loading-transition__skel-title" />
  <CmkSkeleton type="box" class="loading-transition__skel-page-menu" />
  <CmkSkeleton type="box" class="loading-transition__skel-content" />
</template>

<style scoped>
.loading-transition__skel-title {
  margin-top: 6px !important;
  height: 80px !important;
  margin-bottom: 10px !important;
}

.loading-transition__skel-page-menu {
  height: 50px !important;
  margin-bottom: 10px !important;
}

.loading-transition__skel-content {
  height: 100% !important;
}
</style>
