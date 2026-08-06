<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import OverviewSkeleton from '@/monitoring/shared/components/slide-in/OverviewSkeleton.vue'

const GROUPS = [{ rows: 3 }]
</script>

<template>
  <OverviewSkeleton :groups="GROUPS" />
</template>
