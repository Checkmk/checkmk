<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import ActionBar from './ActionBar.vue'
import ActionButton from './ActionButton.vue'
import ContentSpacer from './ContentSpacer.vue'

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

  <ContentSpacer :dimension="11" />
</template>
