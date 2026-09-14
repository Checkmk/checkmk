<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

const { showBack = true, backDisabled = false } = defineProps<{
  showBack?: boolean
  /** Closes the way back while the screen has a save in flight. */
  backDisabled?: boolean
}>()

const emit = defineEmits<{
  back: []
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="trial-mode-selection-dialog-footer">
    <CmkButton v-if="showBack" variant="secondary" :disabled="backDisabled" @click="emit('back')">
      {{ _t('Back') }}
    </CmkButton>
    <div class="trial-mode-selection-dialog-footer__gap" />
    <!-- The screen's own actions, primary last. -->
    <slot />
  </div>
</template>

<style scoped>
.trial-mode-selection-dialog-footer {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  margin-top: var(--dimension-8);
  padding-top: var(--dimension-6);
  border-top: 1px solid var(--ux-theme-6);
}

.trial-mode-selection-dialog-footer__gap {
  flex: 1;
}
</style>
