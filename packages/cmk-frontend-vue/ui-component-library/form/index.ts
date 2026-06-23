/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@ucl/_ucl/types/page'
import type { Folder } from '@ucl/_ucl/types/page'

import UclFormAll from './UclFormAll.vue'
import UclFormBinaryConditions from './UclFormBinaryConditions.vue'
import UclFormBooleanChoice from './UclFormBooleanChoice.vue'
import UclFormCascadingSingleChoice from './UclFormCascadingSingleChoice.vue'
import UclFormCatalog from './UclFormCatalog.vue'
import UclFormCheckboxListChoice from './UclFormCheckboxListChoice.vue'
import UclFormCommentTextArea from './UclFormCommentTextArea.vue'
import UclFormConditionChoices from './UclFormConditionChoices.vue'
import UclFormDataSize from './UclFormDataSize.vue'
import UclFormDatePicker from './UclFormDatePicker.vue'
import UclFormDictionary from './UclFormDictionary.vue'
import UclFormDualListChoice from './UclFormDualListChoice.vue'
import UclFormEditAsync from './UclFormEditAsync.vue'
import UclFormFixedValue from './UclFormFixedValue.vue'
import UclFormFloat from './UclFormFloat.vue'
import UclFormInteger from './UclFormInteger.vue'
import UclFormLabels from './UclFormLabels.vue'
import UclFormList from './UclFormList.vue'
import UclFormListOfStrings from './UclFormListOfStrings.vue'
import UclFormMetric from './UclFormMetric.vue'
import UclFormMultilineText from './UclFormMultilineText.vue'
import UclFormOptionalChoice from './UclFormOptionalChoice.vue'
import UclFormPassword from './UclFormPassword.vue'
import UclFormRegex from './UclFormRegex.vue'
import UclFormSimplePassword from './UclFormSimplePassword.vue'
import UclFormSingleChoice from './UclFormSingleChoice.vue'
import UclFormSingleChoiceEditable from './UclFormSingleChoiceEditable.vue'
import UclFormStaticText from './UclFormStaticText.vue'
import UclFormString from './UclFormString.vue'
import UclFormTimePicker from './UclFormTimePicker.vue'
import UclFormTimeSpan from './UclFormTimeSpan.vue'
import UclFormTimeSpecific from './UclFormTimeSpecific.vue'
import UclFormTuple from './UclFormTuple.vue'

export const pages: Array<Folder | Page> = [
  new Page('FormAll', UclFormAll),
  new Page('FormBinaryConditions', () => UclFormBinaryConditions),
  new Page('FormSingleChoiceEditable', UclFormSingleChoiceEditable),
  new Page('FormCascadingSingleChoice', UclFormCascadingSingleChoice),
  new Page('FormList', UclFormList),
  new Page('FormMetric', UclFormMetric),
  new Page('FormBooleanChoice', UclFormBooleanChoice),
  new Page('FormOptionalChoice', UclFormOptionalChoice),
  new Page('FormConditionChoices', () => UclFormConditionChoices),
  new Page('FormDictionary', UclFormDictionary),
  new Page('FormCheckboxListChoice', UclFormCheckboxListChoice),
  new Page('FormSingleChoice', UclFormSingleChoice),
  new Page('FormTuple', UclFormTuple),
  new Page('FormRegex', UclFormRegex),
  new Page('FormLabels', UclFormLabels),
  new Page('FormEditAsync', UclFormEditAsync),
  new Page('FormListOfStrings', UclFormListOfStrings),
  new Page('FormDualListChoice', UclFormDualListChoice),
  new Page('FormInteger', UclFormInteger),
  new Page('FormFloat', UclFormFloat),
  new Page('FormTimePicker', UclFormTimePicker),
  new Page('FormDatePicker', UclFormDatePicker),
  new Page('FormPassword', UclFormPassword),
  new Page('FormSimplePassword', UclFormSimplePassword),
  new Page('FormCommentTextArea', UclFormCommentTextArea),
  new Page('FormDataSize', UclFormDataSize),
  new Page('FormTimeSpan', UclFormTimeSpan),
  new Page('FormFixedValue', UclFormFixedValue),
  new Page('FormTimeSpecific', UclFormTimeSpecific),
  new Page('FormMultilineText', UclFormMultilineText),
  new Page('FormString', UclFormString),
  new Page('FormStaticText', UclFormStaticText),
  new Page('FormCatalog', UclFormCatalog)
]
