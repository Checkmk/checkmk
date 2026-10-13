/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import type { WizardMode } from '@/quick-setup/components/quick-setup/useWizard'

const cmkWizardStub = defineComponent({ template: '<div><slot /></div>' })
const quickSetupStageStub = defineComponent({
  props: { title: { type: String, required: true } },
  template: '<div>{{ title }}</div>'
})

const renderStages = (regularStages: QuickSetupStageSpec[]) => {
  render(QuickSetup, {
    props: {
      loading: false,
      currentStage: 0,
      regularStages,
      mode: ref<WizardMode>('guided'),
      preventLeaving: false
    },
    global: { stubs: { CmkWizard: cmkWizardStub, QuickSetupStage: quickSetupStageStub } }
  })
}

test('an inapplicable stage is not rendered', () => {
  renderStages([
    { title: 'Applicable stage', is_applicable: true, actions: [], errors: [] },
    { title: 'Inapplicable stage', is_applicable: false, actions: [], errors: [] }
  ])

  screen.getByText('Applicable stage')
  expect(screen.queryByText('Inapplicable stage')).toBeNull()
})

test('a stage without an applicability is rendered', () => {
  // The dashboard wizards share QuickSetupStageSpec and never set the field.
  renderStages([{ title: 'Stage without applicability', actions: [], errors: [] }])

  screen.getByText('Stage without applicability')
})
