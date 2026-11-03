<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'

import GraphsPreview from './GraphsPreview.vue'

const props = defineProps<{
  /** The host whose graphs, or whose service's graphs, the link leads to. */
  host: HostRef
  /** The service whose graphs the link leads to. Omitted for the graphs of the host itself. */
  service?: string | undefined
  /** The page holding the graphs. */
  href: string
}>()

const { _t } = usei18n()

const previewOpen = ref(false)

const label = computed(() =>
  props.service === undefined
    ? _t('Show the graphs of host %{name}', { name: props.host.name })
    : _t('Show the graphs of service %{name}', { name: props.service })
)
</script>

<template>
  <CmkTooltipProvider :delay-duration="300">
    <CmkTooltip v-model:open="previewOpen">
      <CmkTooltipTrigger as-child>
        <CmkIconLink
          :name="service === undefined ? 'host-graph' : 'service-graph'"
          size="medium"
          :href="href"
          target="_top"
          :aria-label="label"
        />
      </CmkTooltipTrigger>
      <!-- The preview loads its graphs only once shown, as the tooltip mounts its content then. -->
      <CmkTooltipContent variant="content" side="right" align="start" use-portal avoid-collisions>
        <GraphsPreview :host="host" :service="service" />
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>
