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

import type { HostState } from '@/monitoring/shared/api/types'

const props = defineProps<{
  state: HostState
  pending?: boolean | undefined
  stale?: boolean | undefined
  /** Two-letter labels, for a state column too tight to spell the state out. */
  abbreviated?: boolean | undefined
}>()

const { _t } = usei18n()

const stateLabel = computed<TranslatedString>(() => {
  if (props.pending) {
    return props.abbreviated ? _t('PD') : _t('PENDING')
  }
  switch (props.state) {
    case 'UP':
      return _t('UP')
    case 'DOWN':
      return props.abbreviated ? _t('DO') : _t('DOWN')
    case 'UNREACHABLE':
    default:
      return props.abbreviated ? _t('UN') : _t('UNREACH')
  }
})

const stateTone = computed<StateTone>(() => {
  if (props.pending) {
    return 'pending'
  }
  switch (props.state) {
    case 'UP':
      return 'ok'
    case 'DOWN':
      return 'critical'
    default:
      return 'unknown'
  }
})

const tagSize = computed<StateTagSize>(() => (props.abbreviated ? 'compact' : 'default'))
</script>

<template>
  <StateTag kind="host" :label="stateLabel" :tone="stateTone" :size="tagSize" :stale="stale" />
</template>
