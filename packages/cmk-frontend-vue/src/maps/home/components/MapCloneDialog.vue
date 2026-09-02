<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Naming the copy of a map: its id (a file name on the site) and its display name.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'

import MapsModal from '@/maps/shared/components/MapsModal.vue'

const props = defineProps<{
  name: string
  alias: string
  error: TranslatedString | null
}>()

const emit = defineEmits<{
  'update:name': [name: string]
  'update:alias': [alias: string]
  confirm: []
  cancel: []
}>()

const { _t } = usei18n()
const nameId = useId()
const aliasId = useId()
</script>

<template>
  <MapsModal open :title="_t('Clone map')" closable @close="emit('cancel')">
    <div class="maps-map-clone-dialog">
      <div class="maps-map-clone-dialog__field">
        <CmkLabel :for="nameId">{{ _t('Map ID') }}</CmkLabel>
        <CmkInput
          :id="nameId"
          :model-value="props.name"
          field-size="fill"
          autofocus
          @update:model-value="emit('update:name', String($event ?? ''))"
          @keydown.enter="emit('confirm')"
        />
      </div>
      <div class="maps-map-clone-dialog__field">
        <CmkLabel :for="aliasId">{{ _t('Display name') }}</CmkLabel>
        <CmkInput
          :id="aliasId"
          :model-value="props.alias"
          field-size="fill"
          @update:model-value="emit('update:alias', String($event ?? ''))"
          @keydown.enter="emit('confirm')"
        />
      </div>
      <CmkAlertBox v-if="props.error" variant="error" :dismissible="false">
        {{ props.error }}
      </CmkAlertBox>
    </div>

    <template #footer>
      <CmkButton variant="secondary" @click="emit('cancel')">{{ _t('Cancel') }}</CmkButton>
      <CmkButton variant="primary" :disabled="!props.name" @click="emit('confirm')">
        {{ _t('Clone') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-map-clone-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.maps-map-clone-dialog__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
