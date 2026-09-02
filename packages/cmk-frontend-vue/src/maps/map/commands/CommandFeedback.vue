<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How a command modal reports back: what went wrong, or that it worked.

Checkmk's rejections are sometimes several lines, and a hint may be appended to
one, so the failure keeps its line breaks rather than running together.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  /** What went wrong. Empty while nothing has. */
  error: TranslatedString
  /** What to say once it worked. Shown only while ``succeeded``. */
  succeededText: TranslatedString
  succeeded: boolean
}>()
</script>

<template>
  <CmkAlertBox v-if="error" variant="error" size="small">
    <span class="maps-command-feedback__error">{{ error }}</span>
  </CmkAlertBox>
  <p v-if="succeeded" class="maps-command-feedback__success">{{ succeededText }}</p>
</template>

<style scoped>
.maps-command-feedback__error {
  white-space: pre-line;
}

.maps-command-feedback__success {
  font-size: var(--font-size-normal);
  color: var(--color-corporate-green-50);
  margin-top: var(--dimension-4);
}
</style>
