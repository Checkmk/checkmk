<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from '@/components/CmkChip.vue'
import { CmkTimeRangeTooltip } from '@/components/date-time'
</script>

<template>
  <CmkTimeRangeTooltip :duration-seconds="14400">
    <CmkChip color="others" variant="outline">Last 4 hours</CmkChip>
  </CmkTimeRangeTooltip>
</template>
