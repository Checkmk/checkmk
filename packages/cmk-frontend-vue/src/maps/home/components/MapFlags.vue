<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map-management flags an administrator sees on a listed map: hidden from
regular users, demo (read-only), and rotation. Shown by both the card grid and
the table, so they are described once.

A card has room for a chip and reads as a tile; a table row does not, and a
chip there would put colour on a fact that carries no state. Hence the two
variants over one set of flags.
-->
<script setup lang="ts">
import type { Colors as ChipColor } from 'cmk-ui-library/components/CmkChip.vue'
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { MapRead } from '@/maps/types/api'

interface Flag {
  id: 'hidden' | 'readonly' | 'rotation'
  label: TranslatedString
  title: string
  color: ChipColor
}

const props = withDefaults(defineProps<{ map: MapRead; variant?: 'chip' | 'text' }>(), {
  variant: 'chip'
})

const { _t } = usei18n()

const flags = computed<Flag[]>(() => {
  const present: Flag[] = []
  if (props.map.show_in_lists === false) {
    present.push({
      id: 'hidden',
      label: _t('Hidden'),
      title: _t('Hidden from regular users'),
      color: 'others'
    })
  }
  if (props.map.readonly) {
    present.push({
      id: 'readonly',
      label: _t('Read-only'),
      title: _t('Demo map — cannot be edited'),
      color: 'others'
    })
  }
  if (props.map.rotation_interval > 0) {
    present.push({
      id: 'rotation',
      label: untranslated(`↻ ${props.map.rotation_interval}s`),
      title: _t('Rotates every %{n} seconds', { n: props.map.rotation_interval }),
      color: 'warning'
    })
  }
  return present
})
</script>

<template>
  <template v-if="variant === 'chip'">
    <CmkChip
      v-for="flag in flags"
      :key="flag.id"
      as-div
      size="small"
      variant="outline"
      :color="flag.color"
      :title="flag.title"
    >
      {{ flag.label }}
    </CmkChip>
  </template>
  <template v-else>
    <span v-for="flag in flags" :key="flag.id" class="maps-map-flags__flag" :title="flag.title">
      {{ flag.label }}
    </span>
  </template>
</template>

<style scoped>
.maps-map-flags__flag {
  flex-shrink: 0;
  color: var(--font-color-dimmed);
}
</style>
