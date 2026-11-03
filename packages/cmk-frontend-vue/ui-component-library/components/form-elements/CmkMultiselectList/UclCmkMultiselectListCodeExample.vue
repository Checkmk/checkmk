<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultiselectList from 'cmk-ui-library/components/user-input/CmkMultiselectList.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

const items = [
  { name: 'state', title: untranslated('State') },
  { name: 'name', title: untranslated('Host') },
  { name: 'alias', title: untranslated('Host alias') }
]

const selected = ref(['state', 'name'])
</script>

<template>
  <CmkMultiselectList
    v-model="selected"
    :items="items"
    :label="untranslated('Columns')"
    :empty-text="untranslated('No matching columns')"
  />
</template>
