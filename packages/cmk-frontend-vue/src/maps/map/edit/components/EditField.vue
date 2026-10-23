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
import useId from 'cmk-ui-library/lib/useId'

defineProps<{
  label: TranslatedString
  help?: TranslatedString | undefined
  required?: boolean
  /** The control takes the slot's ``id``; others name themselves, so the label points at nothing. */
  labelsControl?: boolean
}>()

defineSlots<{
  /** ``id`` goes on the control, so the label names it. */
  default(props: { id: string; label: TranslatedString }): unknown
}>()

const id = useId()
</script>

<template>
  <div class="maps-edit-field">
    <CmkLabel v-bind="labelsControl ? { for: id } : {}" :help="help">
      {{ label }}<CmkLabelRequired v-if="required" space="before" />
    </CmkLabel>
    <slot :id="id" :label="label" />
  </div>
</template>

<style scoped>
.maps-edit-field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
