/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import QuickSetupStage from '@/quick-setup/components/quick-setup/QuickSetupStage.vue'

const cmkWizardStepStub = defineComponent({ template: '<div><slot name="header" /></div>' })

test('an open stage shows its subtitle', () => {
  render(QuickSetupStage, {
    props: {
      index: 0,
      currentStage: 0,
      numberOfStages: 1,
      mode: 'guided',
      loading: false,
      title: 'Stage title',
      sub_title: 'Stage subtitle',
      actions: [],
      errors: []
    },
    global: { stubs: { CmkWizardStep: cmkWizardStepStub } }
  })

  screen.getByText('Stage subtitle')
})
