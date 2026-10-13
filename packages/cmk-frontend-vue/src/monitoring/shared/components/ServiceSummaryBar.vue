<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStateCountBar, {
  type StateCountBarSize,
  type StateSegment,
  type StateTotal
} from 'cmk-ui-library/components/CmkStateCountBar.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { HostRef, ServiceCounts, ServiceState } from '@/monitoring/shared/api/types'
import { hostServicesPageUrl } from '@/monitoring/shared/hostServicesPageUrl'

const props = withDefaults(
  defineProps<{
    counts: ServiceCounts
    /** The host the counts belong to; when named, every count links to its services. */
    host?: HostRef | undefined
    size?: StateCountBarSize
  }>(),
  { host: undefined, size: 'medium' }
)

const { _t } = usei18n()

/**
 * Where a count leads: the host's services, narrowed to one state unless asked for all of
 * them. The link leaves the embedding page rather than opening inside its frame.
 */
function linkTo(state?: ServiceState): Pick<StateSegment, 'href' | 'target'> {
  return props.host === undefined
    ? {}
    : {
        href: hostServicesPageUrl(props.host, state === undefined ? undefined : [state]),
        target: '_top'
      }
}

const segments = computed<StateSegment[]>(() => [
  { label: _t('OK'), count: props.counts.ok, color: 'success', ...linkTo('OK') },
  { label: _t('WARN'), count: props.counts.warn, color: 'warning', ...linkTo('WARN') },
  { label: _t('CRIT'), count: props.counts.crit, color: 'danger', ...linkTo('CRIT') },
  { label: _t('UNKNOWN'), count: props.counts.unknown, color: 'unknown', ...linkTo('UNKNOWN') },
  { label: _t('PENDING'), count: props.counts.pending, color: 'pending', ...linkTo('PENDING') }
])

const allServices = computed<StateTotal | undefined>(() =>
  props.host === undefined ? undefined : { label: _t('All services'), ...linkTo() }
)
</script>

<template>
  <CmkStateCountBar :segments="segments" :total="allServices" :size="size" />
</template>
