<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkProgressbar from '@/components/CmkProgressbar.vue'
</script>

<template>
  <CmkProgressbar :value="30" :max="100" size="medium" :label="{ showTotal: true, unit: '%' }" />
</template>
