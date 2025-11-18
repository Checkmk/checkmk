<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLoading from '@/components/CmkLoading.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <p>Default 8px dots</p>
  <CmkLoading />

  <p>Larger 16px dots</p>
  <CmkLoading height="16px" />
</template>
