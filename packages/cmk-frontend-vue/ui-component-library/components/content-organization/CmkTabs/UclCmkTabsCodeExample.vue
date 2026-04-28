<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkIcon from '@/components/CmkIcon'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'

const activeTab = ref('tab-1')
</script>

<template>
  <CmkTabs v-model="activeTab">
    <template #tabs>
      <CmkTab id="tab-1"> <CmkIcon name="search" /> Search </CmkTab>
      <CmkTab id="tab-2"> <CmkIcon name="info-circle" /> Information </CmkTab>
      <CmkTab id="tab-3" :disabled="true"> <CmkIcon name="close" /> Disabled </CmkTab>
    </template>

    <template #tab-contents>
      <CmkTabContent id="tab-1">
        <p>Use the search bar to find hosts and services.</p>
      </CmkTabContent>
      <CmkTabContent id="tab-2">
        <p>Detailed system information and status reports.</p>
      </CmkTabContent>
      <CmkTabContent id="tab-3">
        <p>This content is not accessible.</p>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>
