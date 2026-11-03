<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'

import ActionBar from './ActionBar.vue'
import ActionButton from './ActionButton.vue'

const { _t } = usei18n()

interface Stage1HeaderEmits {
  save: []
  back: []
}

interface Stage1HeaderProps {
  edit?: boolean
}

defineProps<Stage1HeaderProps>()
const emit = defineEmits<Stage1HeaderEmits>()
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Widget data') }}
  </CmkHeading>

  <ContentSpacer />

  <div class="db-stage2header__actions">
    <ActionBar align-items="left">
      <ActionButton
        :label="_t('Previous step')"
        :icon="{ name: 'continue', side: 'left', rotate: 180 }"
        :action="() => emit('back')"
        variant="secondary"
      />
      <ActionButton
        :label="!!edit ? _t('Save widget') : _t('Add & place widget')"
        :action="() => emit('save')"
        variant="primary"
      />
    </ActionBar>
    <ActionBar align-items="right">
      <slot name="actions" />
    </ActionBar>
  </div>

  <ContentSpacer :dimension="11" />
</template>

<style scoped>
.db-stage2header__actions {
  display: flex;
  justify-content: space-between;
  gap: var(--dimension-4);
}
</style>
