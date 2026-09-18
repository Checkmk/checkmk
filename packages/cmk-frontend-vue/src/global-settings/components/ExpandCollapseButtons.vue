<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const emit = defineEmits<{
  'expand-all': []
  'collapse-all': []
}>()
</script>

<template>
  <div class="global-settings-expand-collapse-buttons">
    <CmkButton variant="optional" @click="emit('collapse-all')">
      {{ _t('Collapse all') }}
    </CmkButton>
    <CmkButton variant="optional" @click="emit('expand-all')">
      {{ _t('Expand all') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.global-settings-expand-collapse-buttons {
  display: flex;
  gap: 8px;
}
</style>
