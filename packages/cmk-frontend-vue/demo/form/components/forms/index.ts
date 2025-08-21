/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@demo/_demo/page'
import type { Folder } from '@demo/_demo/page'

import DemoFormBooleanChoice from './DemoFormBooleanChoice.vue'
import DemoFormCascadingSingleChoice from './DemoFormCascadingSingleChoice.vue'
import DemoFormCheckboxListChoice from './DemoFormCheckboxListChoice.vue'
import DemoFormDictionary from './DemoFormDictionary.vue'
import DemoFormDualListChoice from './DemoFormDualListChoice.vue'
import DemoFormLabels from './DemoFormLabels.vue'
import DemoFormList from './DemoFormList.vue'
import DemoFormMetric from './DemoFormMetric.vue'
import DemoFormOptionalChoice from './DemoFormOptionalChoice.vue'
import DemoFormSingleChoice from './DemoFormSingleChoice.vue'
import DemoFormSingleChoiceEditable from './DemoFormSingleChoiceEditable.vue'
import DemoFormSingleChoiceEditableEditAsync from './DemoFormSingleChoiceEditableEditAsync.vue'
import DemoFormTuple from './DemoFormTuple.vue'

export const pages: Array<Folder | Page> = [
  new Page('FormSingleChoiceEditable', DemoFormSingleChoiceEditable),
  new Page('FormCascadingSingleChoice', DemoFormCascadingSingleChoice),
  new Page('FormList', DemoFormList),
  new Page('FormMetric', DemoFormMetric),
  new Page('FormBoleanChoice', DemoFormBooleanChoice),
  new Page('FormOptionalChoice', DemoFormOptionalChoice),
  new Page('FormDictionary', DemoFormDictionary),
  new Page('FormCheckboxListChoice', DemoFormCheckboxListChoice),
  new Page('FormSingleChoice', DemoFormSingleChoice),
  new Page('FormTuple', DemoFormTuple),
  new Page('FormLabels', DemoFormLabels),
  new Page('FormSingleChoiceEditableEditAsync', DemoFormSingleChoiceEditableEditAsync),
  new Page('FormDualListChoice', DemoFormDualListChoice)
]
