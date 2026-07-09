<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type MonitoringPageLinkButton } from 'cmk-shared-typing/typescript/monitoring/page_link_button'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

const props = defineProps<MonitoringPageLinkButton>()

function navigate(): void {
  window.location.href = props.url
}
</script>

<template>
  <Teleport defer to=".page_state">
    <CmkButton class="monitoring-page-link-button" @click="navigate">
      <CmkMultitoneIcon
        name="experiment"
        primary-color="font"
        secondary-color="hosts"
        size="large"
        class="monitoring-page-link-button__icon"
      />
      {{ title }}
    </CmkButton>
  </Teleport>
</template>

<style scoped>
.monitoring-page-link-button {
  position: absolute;
  right: 50px;
  white-space: nowrap;
}

.monitoring-page-link-button__icon {
  margin-right: var(--dimension-3);
}
</style>
