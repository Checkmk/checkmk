/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@demo/_demo/page'
import type { Folder } from '@demo/_demo/page'

import DemoFormBooleanChoice from './DemoFormBooleanChoice.vue'
import DemoFormCascadingSingleChoice from './DemoFormCascadingSingleChoice.vue'
import DemoFormCatalog from './DemoFormCatalog.vue'
import DemoFormCheckboxListChoice from './DemoFormCheckboxListChoice.vue'
import DemoFormCommentTextArea from './DemoFormCommentTextArea.vue'
import DemoFormDataSize from './DemoFormDataSize.vue'
import DemoFormDatePicker from './DemoFormDatePicker.vue'
import DemoFormDictionary from './DemoFormDictionary.vue'
import DemoFormDualListChoice from './DemoFormDualListChoice.vue'
import DemoFormFixedValue from './DemoFormFixedValue.vue'
import DemoFormFloat from './DemoFormFloat.vue'
import DemoFormInteger from './DemoFormInteger.vue'
import DemoFormLabels from './DemoFormLabels.vue'
import DemoFormList from './DemoFormList.vue'
import DemoFormListOfStrings from './DemoFormListOfStrings.vue'
import DemoFormMetric from './DemoFormMetric.vue'
import DemoFormMultilineText from './DemoFormMultilineText.vue'
import DemoFormOptionalChoice from './DemoFormOptionalChoice.vue'
import DemoFormPassword from './DemoFormPassword.vue'
import DemoFormRegex from './DemoFormRegex.vue'
import DemoFormSimplePassword from './DemoFormSimplePassword.vue'
import DemoFormSingleChoice from './DemoFormSingleChoice.vue'
import DemoFormSingleChoiceEditable from './DemoFormSingleChoiceEditable.vue'
import DemoFormSingleChoiceEditableEditAsync from './DemoFormSingleChoiceEditableEditAsync.vue'
import DemoFormTimePicker from './DemoFormTimePicker.vue'
import DemoFormTimeSpan from './DemoFormTimeSpan.vue'
import DemoFormTimeSpecific from './DemoFormTimeSpecific.vue'
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
  new Page('FormRegex', DemoFormRegex),
  new Page('FormLabels', DemoFormLabels),
  new Page('FormSingleChoiceEditableEditAsync', DemoFormSingleChoiceEditableEditAsync),
  new Page('FormListOfStrings', DemoFormListOfStrings),
  new Page('FormDualListChoice', DemoFormDualListChoice),
  new Page('FormInteger', DemoFormInteger),
  new Page('FormFloat', DemoFormFloat),
  new Page('FormTimePicker', DemoFormTimePicker),
  new Page('FormDatePicker', DemoFormDatePicker),
  new Page('FormPassword', DemoFormPassword),
  new Page('FormSimplePassword', DemoFormSimplePassword),
  new Page('FormCommentTextArea', DemoFormCommentTextArea),
  new Page('FormDataSize', DemoFormDataSize),
  new Page('FormTimeSpan', DemoFormTimeSpan),
  new Page('FormFixedValue', DemoFormFixedValue),
  new Page('FormTimeSpecific', DemoFormTimeSpecific),
  new Page('FormMultilineText', DemoFormMultilineText),
  new Page('FormCatalog', DemoFormCatalog)
]
