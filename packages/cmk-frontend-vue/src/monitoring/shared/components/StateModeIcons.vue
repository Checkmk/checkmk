<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The flapping/stale badges shown beside a state tag - bare, unlinked icons,
status indicators rather than actions (unlike the Mode column's downtime/ack
icons, which link to a view). Shared so the state column's StateCell and the
host/service slide-in headers render the exact same pair.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{
  flapping?: boolean | undefined
  stale?: boolean | undefined
}>()

const { _t } = usei18n()
</script>

<template>
  <CmkIcon
    v-if="flapping"
    class="monitoring-state-mode-icons"
    name="flapping"
    :title="_t('Flapping')"
  />
  <CmkMultitoneIcon
    v-if="stale"
    class="monitoring-state-mode-icons"
    name="stale"
    primary-color="font"
    :title="_t('Stale')"
  />
</template>

<style scoped>
.monitoring-state-mode-icons {
  width: var(--dimension-6);
  height: var(--dimension-6);
}
</style>
