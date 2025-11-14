<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Password } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormPassword from '@/form/private/forms/FormPassword.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<Password>({
  type: 'password',
  title: 'some title',
  help: 'some help',
  validators: [],
  password_store_choices: [
    { password_id: 'demo_password_1', name: 'Demo Password 1' },
    { password_id: 'demo_password_2', name: 'Demo Password 2' }
  ],
  i18n: {
    choose_password_type: 'Choose password type',
    choose_password_from_store: 'Choose password from store',
    explicit_password: 'Explicit',
    password_store: 'From password store',
    no_password_store_choices: 'There are no elements defined for this selection yet.',
    password_choice_invalid: 'Password does not exist or using not permitted.'
  }
})

type PasswordType = 'explicit_password' | 'stored_password'

const data = ref<[PasswordType, string, string, boolean]>([
  'explicit_password',
  '',
  'demo_password',
  false
])

const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: 5
      }
    ]
  } else {
    return []
  }
})

const showValidation = ref<boolean>(false)
</script>

<template>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <FormPassword v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
