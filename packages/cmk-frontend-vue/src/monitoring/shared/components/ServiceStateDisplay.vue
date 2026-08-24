<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import StateTag, { type StateTagSize, type StateTone } from 'cmk-ui-library/components/StateTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { ServiceState } from '@/monitoring/shared/api/types'

const props = defineProps<{
  state: ServiceState
  pending?: boolean | undefined
  stale?: boolean | undefined
  /** Two-letter labels, for a state column too tight to spell the state out. */
  abbreviated?: boolean | undefined
  /** Sized to sit inside a line of text rather than to fill the state column. */
  inline?: boolean | undefined
}>()

const { _t } = usei18n()

const short = computed<boolean>(() => props.abbreviated === true || props.inline === true)

const stateLabel = computed<TranslatedString>(() => {
  if (props.pending) {
    return short.value ? _t('PD') : _t('PENDING')
  }
  switch (props.state) {
    case 'OK':
      return _t('OK')
    case 'WARN':
      return short.value ? _t('WA') : _t('WARNING')
    case 'CRIT':
      return short.value ? _t('CR') : _t('CRITICAL')
    case 'UNKNOWN':
    default:
      return short.value ? _t('UN') : _t('UNKNOWN')
  }
})

const stateTone = computed<StateTone>(() => {
  if (props.pending) {
    return 'pending'
  }
  switch (props.state) {
    case 'OK':
      return 'ok'
    case 'WARN':
      return 'warning'
    case 'CRIT':
      return 'critical'
    default:
      return 'unknown'
  }
})

const tagSize = computed<StateTagSize>(() => {
  if (props.inline) {
    return 'inline'
  }
  return props.abbreviated ? 'compact' : 'default'
})
</script>

<template>
  <StateTag kind="service" :label="stateLabel" :tone="stateTone" :size="tagSize" :stale="stale" />
</template>
