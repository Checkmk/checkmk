<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

const props = defineProps<{ type: 'success' | 'warning'; title: string; info: string }>()
</script>

<template>
  <div>
    <CmkAlert
      v-if="props.type === 'success'"
      variant="success"
      class="mm-changes-activation-result"
      :dismissible="true"
      :heading="untranslated(props.title)"
      :text="untranslated(props.info)"
    />
    <CmkAlert
      v-else
      variant="warning"
      class="mm-changes-activation-result"
      :heading="untranslated(props.title)"
      :text="untranslated(props.info)"
    />
  </div>
</template>

<style scoped>
.mm-changes-activation-result {
  width: 100%;
  box-sizing: border-box;
}
</style>
