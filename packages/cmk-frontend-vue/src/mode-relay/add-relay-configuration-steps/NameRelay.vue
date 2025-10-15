<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const { _t } = usei18n()

const relayName = defineModel<string>({ default: '' })
</script>

<template>
  <CmkParagraph>
    {{ _t('Provide a display name for your Relay.') }}
  </CmkParagraph>
  <div class="mode-relay-name-relay__form-row">
    <CmkLabel>
      {{ _t('Relay display name') }}
      <CmkLabelRequired />
    </CmkLabel>
    <CmkInput v-model="relayName" type="text" field-size="MEDIUM" />
  </div>
  <CmkAlertBox variant="info">
    {{
      _t(
        'The name you enter here will be automatically inserted into the terminal code in the next step.'
      )
    }}
  </CmkAlertBox>
</template>

<style scoped>
.mode-relay-name-relay__form-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-6);
}
</style>
