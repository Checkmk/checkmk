<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPerfometer from '@/components/CmkPerfometer.vue'
</script>

<template>
  <CmkPerfometer :value="75" :value-range="[0, 100]" formatted="75 %" color="green" />
</template>
