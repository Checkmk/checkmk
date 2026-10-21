<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import AiDockPanel from '@/ai/components/AiDockPanel.vue'

const size = ref(180)
</script>

<template>
  <div style="position: relative; width: 100%; height: 300px">
    <p>Main content</p>
    <AiDockPanel v-model:size="size" dock="bottom" :min-size="120">
      <p>Docked panel</p>
    </AiDockPanel>
  </div>
</template>
