<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <StringCell
          value="example.host.checkmk.com / Filesystem /var/log — long_descriptive_label"
          :hard-break-every="15"
          :linked-to="{ href: 'https://checkmk.com', target: '_blank', variant: 'icon' }"
        />
      </tr>
    </tbody>
  </table>
</template>
