<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A monitoring state, as the shared state tag.

Maps carry the daemon's state vocabulary, which is wider than the host and the
service vocabularies the monitoring views use: the same tag has to render a
host's UP, a service's CRITICAL, and the two states only a map can be in — an
object monitoring does not know, and one this user may not see. This is the one
place that maps that vocabulary onto the tag's tone and label.
-->
<script setup lang="ts">
import StateTag, { type StateTagSize, type StateTone } from 'cmk-ui-library/components/StateTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    state: string | undefined
    /** Fixes the tag's width; a host's longest label is shorter than a service's. */
    kind: 'host' | 'service'
    size?: StateTagSize
    /** Renders the state as no longer backed by a fresh check result. */
    stale?: boolean | undefined
  }>(),
  { size: 'default' }
)

const { _t } = usei18n()

// The narrowed sizes fit two letters, so they take the two-letter labels the
// monitoring views use there; a spelled-out state would be cut off.
const short = computed<boolean>(() => props.size === 'compact' || props.size === 'inline')

// Upper-case, like the monitoring views' own tags.
const label = computed<TranslatedString>(() => {
  switch (props.state) {
    case 'UP':
      return _t('UP')
    case 'DOWN':
      return short.value ? _t('DO') : _t('DOWN')
    case 'UNREACHABLE':
      return short.value ? _t('UN') : _t('UNREACH')
    case 'OK':
      return _t('OK')
    case 'WARNING':
      return short.value ? _t('WA') : _t('WARNING')
    case 'CRITICAL':
      return short.value ? _t('CR') : _t('CRITICAL')
    case 'UNKNOWN':
      return short.value ? _t('UN') : _t('UNKNOWN')
    case 'NOT_FOUND':
      return short.value ? _t('NF') : _t('NOT FOUND')
    case 'NO_PERMISSION':
      return short.value ? _t('NP') : _t('NO ACCESS')
    default:
      return short.value ? _t('PD') : _t('PENDING')
  }
})

const tone = computed<StateTone>(() => {
  switch (props.state) {
    case 'UP':
    case 'OK':
      return 'ok'
    case 'DOWN':
    case 'CRITICAL':
      return 'critical'
    case 'WARNING':
      return 'warning'
    case 'UNREACHABLE':
    case 'UNKNOWN':
    case 'NO_PERMISSION':
      return 'unknown'
    default:
      return 'pending'
  }
})
</script>

<template>
  <StateTag :kind="kind" :label="label" :tone="tone" :size="size" :stale="stale" />
</template>
