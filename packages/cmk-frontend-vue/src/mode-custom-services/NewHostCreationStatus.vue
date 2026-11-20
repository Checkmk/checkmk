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
    <CmkIcon v-if="status === 'created'" name="checkmark" variant="inline" />
    <span>{{ _t('New host creation') }}</span>
    <CmkLoading v-if="status === 'creating'" />
  </div>
</template>

<style scoped>
.mode-custom-services-new-host-creation-status {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.mode-custom-services-new-host-creation-status--created {
  color: var(--success);
}
</style>
