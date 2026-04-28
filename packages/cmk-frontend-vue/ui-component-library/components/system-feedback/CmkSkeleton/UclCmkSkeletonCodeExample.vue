<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'
</script>

<template>
  <div class="user-card-loading">
    <CmkSkeleton type="icon-xlarge" />
    <div class="user-card-text">
      <CmkSkeleton type="h3" width="60%" />
      <CmkSkeleton type="info-text" width="40%" />
    </div>
  </div>
</template>
