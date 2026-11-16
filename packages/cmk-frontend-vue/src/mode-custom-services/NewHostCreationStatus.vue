<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostCreationStatus } from './save'

const { status } = defineProps<{ status: HostCreationStatus }>()

const { _t } = usei18n()
</script>

<template>
  <div
    class="mode-custom-services-new-host-creation-status"
    :class="`mode-custom-services-new-host-creation-status--${status}`"
    role="status"
  >
    <div class="mode-custom-services-new-host-creation-status__line">
      <CmkIcon v-if="status === 'created'" name="checkmark" variant="inline" />
      <CmkIcon v-else-if="status === 'refused'" name="cross" variant="inline" />
      <span>{{ _t('New host creation') }}</span>
      <CmkLoading v-if="status === 'creating'" />
    </div>
    <span v-if="status === 'refused'">
      {{ _t('Some hosts could not be created. Try again, or verify your configuration.') }}
    </span>
  </div>
</template>

<style scoped>
.mode-custom-services-new-host-creation-status {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.mode-custom-services-new-host-creation-status__line {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.mode-custom-services-new-host-creation-status--created {
  color: var(--success);
}

.mode-custom-services-new-host-creation-status--refused {
  color: var(--color-danger);
}
</style>
