<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Unreachable sites, said in the topbar beside the live indicator: a banner over
the map would cover the objects and the search it sits above, for as long as
the site stays down.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { type DeadSiteHosts, deadSitesMessage } from './deadSites'

const { _t, _tn } = usei18n()

const props = defineProps<{
  deadSites: string[]
  deadSiteHosts: DeadSiteHosts
}>()

const message = computed(() => deadSitesMessage(_t, props.deadSites, props.deadSiteHosts))
</script>

<template>
  <span class="maps-map-sites-pill" role="status" :aria-label="message" :title="message">
    <CmkIcon name="problem" size="small" />
    {{
      _tn('%{n} site unreachable', '%{n} sites unreachable', deadSites.length, {
        n: deadSites.length
      })
    }}
  </span>
</template>

<style scoped>
.maps-map-sites-pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 7px;
  font-size: var(--font-size-normal);
  font-weight: 500;
  line-height: 16px;
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}
</style>
