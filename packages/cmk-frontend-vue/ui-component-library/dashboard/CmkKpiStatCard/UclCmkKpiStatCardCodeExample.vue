<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard'

const series = [62, 68, 75, 71, 66, 73, 82, 78, 74, 80].map((value, index) => ({
  timestamp: index * 60,
  value
}))
</script>

<template>
  <CmkKpiStatCard
    value="801.84"
    unit="GB"
    :delta-ratio="0.062"
    :series="series"
    color="var(--color-corporate-green-50)"
    :state="{ severity: 'warn' }"
    :range-limits="{ minimum: '0 B', maximum: '1.00 TB' }"
    href="view.py?view_name=service"
  />
</template>
