<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <BaseCell :breakpoints="{ S: 50, M: 100, L: 200, XL: 400 }">
          <template #XL>host-01.example.com — Linux web server</template>
          <template #L>host-01.example.com (web)</template>
          <template #M>host-01.example.com</template>
          <template #S>host-01</template>
          <template #default>01</template>
        </BaseCell>
      </tr>
    </tbody>
  </table>
</template>
