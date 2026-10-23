<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'

import RichTextCell from '@/monitoring/shared/components/cell/RichTextCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <RichTextCell value="example.host.checkmk.com / Filesystem /var/log" />
      </tr>
      <tr>
        <RichTextCell>
          <CmkTag color="danger" variant="weighted" content="CRIT" size="small" />
          CPU utilization is 95% —
          <a href="https://checkmk.com" target="_blank">view graph</a>
        </RichTextCell>
      </tr>
    </tbody>
  </table>
</template>
