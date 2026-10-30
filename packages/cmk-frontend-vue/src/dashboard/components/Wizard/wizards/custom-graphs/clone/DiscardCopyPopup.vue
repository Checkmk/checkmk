<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkPopup from 'cmk-ui-library/components/CmkPopup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { DialogTitle } from 'reka-ui'

const { _t } = usei18n()

defineProps<{ open: boolean }>()

const emit = defineEmits<{
  confirm: []
  close: []
}>()
</script>

<template>
  <CmkPopup :open="open" @close="emit('close')">
    <div class="db-discard-copy-popup">
      <DialogTitle>
        <CmkHeading type="h2">{{ _t('Discard your changes?') }}</CmkHeading>
      </DialogTitle>
      <CmkParagraph>{{
        _t(
          'You have unsaved changes to this cloned graph. Changing the graph source will discard them.'
        )
      }}</CmkParagraph>
      <div class="db-discard-copy-popup__buttons">
        <CmkButton variant="danger" @click="emit('confirm')">{{ _t('Discard changes') }}</CmkButton>
        <CmkButton variant="secondary" @click="emit('close')">{{ _t('Keep editing') }}</CmkButton>
      </div>
    </div>
  </CmkPopup>
</template>

<style scoped>
.db-discard-copy-popup {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.db-discard-copy-popup__buttons {
  display: flex;
  gap: var(--dimension-4);
}
</style>
