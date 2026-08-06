<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'

import OverviewSkeleton from '@/monitoring/shared/components/slide-in/OverviewSkeleton.vue'

const GROUPS = [{ rows: 4 }, { rows: 3 }, { rows: 3, chips: true }]
</script>

<template>
  <OverviewSkeleton :groups="GROUPS">
    <template #before>
      <div class="monitoring-host-overview-skeleton__link">
        <CmkSkeleton type="text" width="120px" />
      </div>
    </template>
  </OverviewSkeleton>
</template>

<style scoped>
.monitoring-host-overview-skeleton__link {
  display: flex;
  justify-content: flex-end;
}
</style>
