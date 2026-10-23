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
            bars: [
              [
                { share: 65, color: '#13d389' },
                { share: 35, color: null }
              ]
            ],
            formatted: '65.0%'
          }"
        />
      </tr>
    </tbody>
  </table>
</template>
