<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'

const { _t } = usei18n()

defineProps<{ isEditMode: boolean }>()

const emit = defineEmits<{
  goPrev: []
  addWidget: []
}>()
</script>

<template>
  <CmkHeading type="h1">{{ _t('Visualization') }}</CmkHeading>
  <ContentSpacer />
  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'continue', side: 'left', rotate: 180 }"
      variant="secondary"
      :action="() => emit('goPrev')"
    />
    <ActionButton
      :label="isEditMode ? _t('Save widget') : _t('Add & place widget')"
      variant="primary"
      :action="() => emit('addWidget')"
    />
  </ActionBar>
</template>
