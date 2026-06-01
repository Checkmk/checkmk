<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <StateCell :state="'UP'" />
      </tr>
      <tr>
        <StateCell :state="'DOWN'" />
      </tr>
      <tr>
        <StateCell :state="'UNREACHABLE'" :stale="true" />
      </tr>
    </tbody>
  </table>
</template>
