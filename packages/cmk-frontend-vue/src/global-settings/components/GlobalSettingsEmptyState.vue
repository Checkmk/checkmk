<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const emit = defineEmits<{ reset: [] }>()
</script>

<template>
  <div class="global-settings-empty-state" aria-live="polite">
    <CmkIcon name="global-settings" size="xxlarge" aria-hidden="true" />
    <p class="global-settings-empty-state__title">{{ _t('No matching settings found.') }}</p>
    <CmkButton class="global-settings-empty-state__reset" @click="emit('reset')">
      {{ _t('Reset search') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.global-settings-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-6);
  padding: var(--dimension-10) 0;
}

.global-settings-empty-state__title {
  margin: 0;
  font-weight: var(--font-weight-bold);
}
</style>
