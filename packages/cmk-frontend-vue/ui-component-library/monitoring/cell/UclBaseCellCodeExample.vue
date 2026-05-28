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
        <BaseCell
          :linked-to="{ href: 'https://checkmk.com', target: '_self' }"
          :highlight="{ type: 'inline', color: 'success' }"
        >
          host-01.example.com
        </BaseCell>
      </tr>
    </tbody>
  </table>
</template>
