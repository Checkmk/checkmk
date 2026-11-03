<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSplitPane from 'cmk-ui-library/components/CmkSplitPane.vue'
import { ref } from 'vue'

const collapsed = ref(false)
</script>

<template>
  <div style="width: 100%; height: 300px">
    <CmkSplitPane v-model:collapsed="collapsed" :pane-min-size="20" :pane-max-size="50">
      <template #left>
        <p>Main content</p>
      </template>
      <template #right>
        <p>Collapsible side panel</p>
      </template>
    </CmkSplitPane>
  </div>
</template>
