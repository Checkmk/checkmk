<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Why part of a map's state is not current: the daemon is out of reach, or sites
behind it are. The topbar only says "Offline", and an unreachable site says
nothing at all there, while its hosts go grey or, on a geo automap, vanish.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { LiveStatus } from '@/maps/services/MapStatesService'

import { type DeadSiteHosts, connectionMessage, deadSitesMessage } from './deadSites'

const { _t } = usei18n()

const props = defineProps<{
  status: LiveStatus
  deadSites: string[]
  deadSiteHosts: DeadSiteHosts
}>()

const connectionText = computed(() => connectionMessage(_t, props.status))
const deadSitesText = computed(() => deadSitesMessage(_t, props.deadSites, props.deadSiteHosts))
</script>

<template>
  <CmkAlert v-if="connectionText" variant="warning" size="small" :text="connectionText" />
  <CmkAlert v-else-if="deadSites.length" variant="warning" :text="deadSitesText" />
</template>
