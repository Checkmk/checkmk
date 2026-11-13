<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Unreachable sites, said in the topbar for as long as the site stays down.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapWarningPill from './MapWarningPill.vue'
import { type DeadSiteHosts, deadSitesMessage } from './deadSites'

const { _t, _tn } = usei18n()

const props = defineProps<{
  deadSites: string[]
  deadSiteHosts: DeadSiteHosts
}>()

const message = computed(() => deadSitesMessage(_t, props.deadSites, props.deadSiteHosts))
</script>

<template>
  <MapWarningPill :message="message">
    {{
      _tn('%{n} site unreachable', '%{n} sites unreachable', deadSites.length, {
        n: deadSites.length
      })
    }}
  </MapWarningPill>
</template>
