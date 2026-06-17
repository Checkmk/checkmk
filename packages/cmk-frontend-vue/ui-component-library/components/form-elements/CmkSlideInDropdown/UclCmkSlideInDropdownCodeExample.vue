<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkSlideInDropdown from '@/components/user-input/CmkSlideInDropdown'

const selectedId = ref<string | null>(null)

const choices = [
  { name: 'entity_1', title: untranslated('First entity') },
  { name: 'entity_2', title: untranslated('Second entity') }
]
</script>

<template>
  <CmkSlideInDropdown
    v-model="selectedId"
    :choices="choices"
    label="Notification parameter"
    :allow-editing-existing-elements="true"
    :new-title="untranslated('New parameter')"
    :edit-title="untranslated('Edit parameter')"
  >
    <template #slide-in="{ objectId, close }">
      <!-- Provide any form here, e.g. FormEditAsync -->
      <div>
        <p>Editing {{ objectId ?? 'a new element' }}.</p>
        <button @click="close">Close</button>
      </div>
    </template>
  </CmkSlideInDropdown>
</template>
