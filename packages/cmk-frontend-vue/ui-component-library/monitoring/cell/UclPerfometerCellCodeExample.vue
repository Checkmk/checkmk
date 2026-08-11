<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import PerfometerCell from '@/monitoring/shared/components/cell/PerfometerCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <PerfometerCell
          :data="{
            value: 65,
            value_range: { min: 0, max: 100 },
            formatted: '65.0%',
            color: '#13d389'
          }"
        />
      </tr>
    </tbody>
  </table>
</template>
