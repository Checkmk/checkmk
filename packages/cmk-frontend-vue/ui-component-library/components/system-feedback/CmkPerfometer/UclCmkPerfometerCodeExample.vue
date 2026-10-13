<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPerfometer from 'cmk-ui-library/components/CmkPerfometer.vue'
</script>

<template>
  <CmkPerfometer :value="75" :value-range="[0, 100]" formatted="75 %" color="green" />
  <CmkPerfometer
    :bars="[
      [
        { share: 70, color: 'green' },
        { share: 30, color: null }
      ],
      [
        { share: 35, color: 'orange' },
        { share: 65, color: null }
      ]
    ]"
    formatted="70 % / 35 %"
  />
</template>
