<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import LabelCell from '@/monitoring/shared/components/cell/LabelCell.vue'
</script>

<template>
  <table>
    <tbody>
      <tr>
        <LabelCell
          column-id="labels"
          :items="[
            { text: 'cmk/azure/vm: instance', color: 'discovered' },
            { text: 'cmk/site: master', color: 'discovered' },
            { text: 'owner: platform', color: 'explicit', variant: 'outline' }
          ]"
        />
      </tr>
    </tbody>
  </table>
</template>
