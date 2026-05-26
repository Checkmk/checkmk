<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import NumberCell from '@/monitoring/shared/components/cell/NumberCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <NumberCell
          :value="42"
          :decimals="0"
          :highlight="{ type: 'inline', color: 'success' }"
          :linked-to="{ href: 'https://checkmk.com', target: '_blank' }"
        />
      </tr>
    </tbody>
  </table>
</template>
