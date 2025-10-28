<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

const COLS = 8
const ROWS = 6

const randomWidth = () => `${20 + Math.random() * 80}px`
</script>

<template>
  <table>
    <tbody>
      <tr>
        <th v-for="nTd in COLS" :key="`th-${nTd}`">
          <CmkSkeleton type="text" :width="randomWidth()" />
        </th>
      </tr>
      <tr v-for="nTr in ROWS" :key="nTr">
        <td v-for="nTd in COLS" :key="`tr-${nTr}-${nTd}`">
          <CmkSkeleton type="text" :width="randomWidth()" />
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
}

th,
td {
  padding: 0 8px;
  text-align: left;
  vertical-align: middle;
}

th {
  height: 24px;
  background: var(--ux-theme-2);
}

td {
  height: 24px;
}

tr:nth-child(even) {
  background: var(--ux-theme-3);
}

tr:nth-child(odd) {
  background: var(--ux-theme-4);
}
</style>
