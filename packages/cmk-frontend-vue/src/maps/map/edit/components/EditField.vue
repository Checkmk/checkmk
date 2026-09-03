<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One labelled field of the editing UI: the label with its help text behind it,
and the control below.

Matches how FormSpec lays out its own fields, so the hand-written blocks sit
beside the generated ones without a seam — used by the map settings and by the
panel that adds an object.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  label: TranslatedString
  help?: TranslatedString | undefined
  required?: boolean
}>()
</script>

<template>
  <div class="maps-edit-field">
    <CmkLabel :help="help">
      {{ label }}<CmkLabelRequired v-if="required" space="before" />
    </CmkLabel>
    <slot />
  </div>
</template>

<style scoped>
.maps-edit-field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
