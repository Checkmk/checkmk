<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <IconCell
          :icons="[
            {
              icon_name: 'downtime',
              link: 'view.py?view_name=downtimes_of_host&host=web-server-01',
              title: 'In scheduled downtime'
            },
            {
              icon_name: 'ack',
              link: 'view.py?view_name=host&host=web-server-01',
              title: 'Problem acknowledged'
            }
          ]"
        />
      </tr>
      <tr>
        <IconCell :icons="[{ icon_name: 'alert-crit', title: 'Service alert' }]" />
      </tr>
    </tbody>
  </table>
</template>
