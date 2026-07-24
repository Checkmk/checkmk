<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const props = defineProps<MonitoringHostServicesApp>()

function navigateToLegacy(): void {
  if (props.legacy_view_button) {
    window.location.href = props.legacy_view_button.url
  }
}
</script>

<template>
  <Teleport v-if="legacy_view_button" defer to=".titlebar">
    <CmkButton class="monitoring-host-services-app__legacy-view-button" @click="navigateToLegacy">
      <CmkIcon name="back" class="monitoring-host-services-app__legacy-view-button-icon" />
      {{ legacy_view_button.title }}
    </CmkButton>
  </Teleport>
  <div class="monitoring-host-services-app">
    <p class="monitoring-host-services-app__placeholder">
      {{ _t('Services of host %{host} on site %{site}', { host, site }) }}
    </p>
  </div>
</template>

<style scoped>
.monitoring-host-services-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.monitoring-host-services-app__legacy-view-button {
  right: var(--dimension-4);
  white-space: nowrap;
  align-self: center;
}

.monitoring-host-services-app__legacy-view-button-icon {
  margin-right: var(--dimension-3);
}
</style>
