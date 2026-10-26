<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a command dialog acts on, named like its other fields: what kind of object
above, which one below.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MapElement } from '@/maps/types/api'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { getEffectiveObjectType, getMapElementName } from '@/maps/utils/naming'

const props = defineProps<{ object: MapElement }>()

const { _t } = usei18n()

// A line or graph bound to a host or service acts on that.
const kind = computed(() => objectTypeLabel(getEffectiveObjectType(props.object), _t))
// An unnamed object, like a dynamic group, would only repeat the kind.
const name = computed(() => getMapElementName(props.object))
</script>

<template>
  <div class="maps-command-object-name">
    <span class="maps-command-object-name__kind">{{ kind }}</span>
    <span v-if="name">{{ name }}</span>
  </div>
</template>

<style scoped>
.maps-command-object-name {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  font-size: var(--font-size-normal);
}

.maps-command-object-name__kind {
  font-weight: var(--font-weight-bold);
}
</style>
