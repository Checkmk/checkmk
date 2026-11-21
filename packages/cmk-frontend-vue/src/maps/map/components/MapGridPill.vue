<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Said when a grid of the map matches more objects than it shows, or could not
read them, so a missing host is not mistaken for one the filter left out.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import { GRID_MEMBER_LIMIT } from '@/maps/map/static/gridMembers'

import MapWarningPill from './MapWarningPill.vue'

defineProps<{
  failed: boolean
  canEdit: boolean
}>()

const { _t } = usei18n()
</script>

<template>
  <MapWarningPill
    v-if="failed"
    :message="
      canEdit
        ? _t(
            'Livestatus could not read the objects a grid of this map adds. The editor shows which grid it is.'
          )
        : _t('Livestatus could not read the objects a grid of this map adds.')
    "
  >
    {{ _t('Grid failed') }}
  </MapWarningPill>
  <MapWarningPill
    v-else
    :message="
      _t('A grid matches more than %{n} objects, so the map shows only some of them.', {
        n: GRID_MEMBER_LIMIT
      })
    "
  >
    {{ _t('Not all objects shown') }}
  </MapWarningPill>
</template>
