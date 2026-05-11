/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import { pages as formSpecPages } from '../form'
import UclColors from '../foundations/Colors/UclColors.vue'
import { pages as i18nPages } from '../i18n'
import { pages as twoFactorAuthPages } from '../two-factor-authentication'
import UclCmkBadge from './basic-elements/CmkBadge/UclCmkBadge.vue'
import UclCmkButton from './basic-elements/CmkButton/UclCmkButton.vue'
import UclCmkButtonCancel from './basic-elements/CmkButtonCancel/UclCmkButtonCancel.vue'
import UclCmkButtonSubmit from './basic-elements/CmkButtonSubmit/UclCmkButtonSubmit.vue'
import UclCmkChip from './basic-elements/CmkChip/UclCmkChip.vue'
import UclCmkCode from './basic-elements/CmkCode/UclCmkCode.vue'
import UclCmkColorPicker from './basic-elements/CmkColorPicker/UclCmkColorPicker.vue'
import UclCmkIconButton from './basic-elements/CmkIconButton/UclCmkIconButton.vue'
import UclCmkInlineButton from './basic-elements/CmkInlineButton/UclCmkInlineButton.vue'
import UclCmkLink from './basic-elements/CmkLink/UclCmkLink.vue'
import UclCmkSwitch from './basic-elements/CmkSwitch/UclCmkSwitch.vue'
import UclCmkTag from './basic-elements/CmkTag/UclCmkTag.vue'
import UclCmkAccordion from './content-organization/CmkAccordion/UclCmkAccordion.vue'
import UclCmkAccordionStepPanel from './content-organization/CmkAccordionStepPanel/UclCmkAccordionStepPanel.vue'
import UclCmkCatalogPanel from './content-organization/CmkCatalogPanel/UclCmkCatalogPanel.vue'
import UclCmkCollapsible from './content-organization/CmkCollapsible/UclCmkCollapsible.vue'
import UclCmkScrollContainer from './content-organization/CmkScrollContainer/UclCmkScrollContainer.vue'
import UclCmkSlideIn from './content-organization/CmkSlideIn/UclCmkSlideIn.vue'
import UclCmkSlideInDialog from './content-organization/CmkSlideInDialog/UclCmkSlideInDialog.vue'
import UclCmkTabs from './content-organization/CmkTabs/UclCmkTabs.vue'
import UclCmkWizard from './content-organization/CmkWizard/UclCmkWizard.vue'
import UclCmkCheckbox from './form-elements/CmkCheckbox/UclCmkCheckbox.vue'
import UclCmkConfigurationEntityDropdown from './form-elements/CmkConfigurationEntityDropdown/UclCmkConfigurationEntityDropdown.vue'
import UclCmkDateTimePicker from './form-elements/CmkDateTimePicker/UclCmkDateTimePicker.vue'
import UclCmkDropdown from './form-elements/CmkDropdown/UclCmkDropdown.vue'
import UclCmkDualList from './form-elements/CmkDualList/UclCmkDualList.vue'
import UclCmkInput from './form-elements/CmkInput/UclCmkInput.vue'
import UclCmkList from './form-elements/CmkList/UclCmkList.vue'
import UclCmkTimeSpan from './form-elements/CmkTimeSpan/UclCmkTimeSpan.vue'
import UclCmkToggleButtonGroup from './form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroup.vue'
import UclCmkHtml from './foundation-elements/CmkHtml/UclCmkHtml.vue'
import UclCmkIcon from './foundation-elements/CmkIcon/UclCmkIcon.vue'
import UclCmkIconEmblem from './foundation-elements/CmkIcon/UclCmkIconEmblem.vue'
import UclCmkMultitoneIcon from './foundation-elements/CmkIcon/UclCmkMultitoneIcon.vue'
import UclCmkIndent from './foundation-elements/CmkIndent/UclCmkIndent.vue'
import UclCmkKeyboardKey from './foundation-elements/CmkKeyboardKey/UclCmkKeyboardKey.vue'
import UclCmkLabel from './foundation-elements/CmkLabel/UclCmkLabel.vue'
import UclCmkLabelRequired from './foundation-elements/CmkLabelRequired/UclCmkLabelRequired.vue'
import UclCmkSpace from './foundation-elements/CmkSpace/UclCmkSpace.vue'
import UclCmkZebra from './foundation-elements/CmkZebra/UclCmkZebra.vue'
import UclCmkHeading from './foundation-elements/typography/UclCmkHeading.vue'
import UclCmkParagraph from './foundation-elements/typography/UclCmkParagraph.vue'
import UclArrowDown from './graphics/ArrowDown/UclArrowDown.vue'
import UclCmkLinkCard from './navigation/CmkLinkCard/UclCmkLinkCard.vue'
import UclCmkAlertBox from './system-feedback/CmkAlertBox/UclCmkAlertBox.vue'
import UclCmkCopy from './system-feedback/CmkCopy/UclCmkCopy.vue'
import UclCmkDialog from './system-feedback/CmkDialog/UclCmkDialog.vue'
import UclCmkErrorBoundary from './system-feedback/CmkErrorBoundary/UclCmkErrorBoundary.vue'
import UclCmkHelpText from './system-feedback/CmkHelpText/UclCmkHelpText.vue'
import UclCmkInlineValidation from './system-feedback/CmkInlineValidation/UclCmkInlineValidation.vue'
import UclCmkLoading from './system-feedback/CmkLoading/UclCmkLoading.vue'
import UclCmkPerfometer from './system-feedback/CmkPerfometer/UclCmkPerfometer.vue'
import UclCmkPopup from './system-feedback/CmkPopup/UclCmkPopup.vue'
import UclCmkPopupDialog from './system-feedback/CmkPopupDialog/UclCmkPopupDialog.vue'
import UclCmkProgressbar from './system-feedback/CmkProgressbar/UclCmkProgressbar.vue'
import UclCmkSkeleton from './system-feedback/CmkSkeleton/UclCmkSkeleton.vue'
import UclCmkTooltip from './system-feedback/CmkTooltip/UclCmkTooltip.vue'

const basicElementsPages = [
  new Page('CmkBadge', UclCmkBadge),
  new Page('CmkButton', UclCmkButton),
  new Page('CmkButtonCancel', UclCmkButtonCancel),
  new Page('CmkButtonSubmit', UclCmkButtonSubmit),
  new Page('CmkIconButton', UclCmkIconButton),
  new Page('CmkInlineButton', UclCmkInlineButton),
  new Page('CmkChip', UclCmkChip),
  new Page('CmkCode', UclCmkCode),
  new Page('CmkColorPicker', UclCmkColorPicker),
  new Page('CmkLink', UclCmkLink),
  new Page('CmkSwitch', UclCmkSwitch),
  new Page('CmkTag', UclCmkTag)
]

const contentOrganizationPages = [
  new Page('CmkAccordion', UclCmkAccordion),
  new Page('CmkAccordionStepPanel', UclCmkAccordionStepPanel),
  new Page('CmkTabs', UclCmkTabs),
  new Page('CmkCatalogPanel', UclCmkCatalogPanel),
  new Page('CmkCollapsible', UclCmkCollapsible),
  new Page('CmkScrollContainer', UclCmkScrollContainer),
  new Page('CmkSlideIn', UclCmkSlideIn),
  new Page('CmkSlideInDialog', UclCmkSlideInDialog),
  new Page('CmkWizard', UclCmkWizard)
]

const formElementsPages = [
  new Page('CmkCheckbox', UclCmkCheckbox),
  new Page('CmkConfigurationEntityDropdown', UclCmkConfigurationEntityDropdown),
  new Page('CmkDateTimePicker', UclCmkDateTimePicker),
  new Page('CmkDropdown', UclCmkDropdown),
  new Page('CmkDualList', UclCmkDualList),
  new Page('CmkInput', UclCmkInput),
  new Page('CmkList', UclCmkList),
  new Page('CmkTimeSpan', UclCmkTimeSpan),
  new Page('CmkToggleButtonGroup', UclCmkToggleButtonGroup)
]

const foundationsPages = [new Page('Colors', UclColors)]

const foundationElementsPages = [
  new Page('CmkIcon', UclCmkIcon),
  new Page('CmkIconEmblem', UclCmkIconEmblem),
  new Page('CmkMultitoneIcon', UclCmkMultitoneIcon),
  new Page('CmkHeading', UclCmkHeading),
  new Page('CmkParagraph', UclCmkParagraph),
  new Page('CmkHtml', UclCmkHtml),
  new Page('CmkIndent', UclCmkIndent),
  new Page('CmkKeyboardKey', UclCmkKeyboardKey),
  new Page('CmkLabel', UclCmkLabel),
  new Page('CmkLabelRequired', UclCmkLabelRequired),
  new Page('CmkSpace', UclCmkSpace),
  new Page('CmkZebra', UclCmkZebra)
]

const graphicsPages = [new Page('ArrowDown', UclArrowDown)]

const navigationPages = [new Page('CmkLinkCard', UclCmkLinkCard)]

const systemFeedbackPages = [
  new Page('CmkAlertBox', UclCmkAlertBox),
  new Page('CmkCopy', UclCmkCopy),
  new Page('CmkDialog', UclCmkDialog),
  new Page('CmkErrorBoundary', UclCmkErrorBoundary),
  new Page('CmkHelpText', UclCmkHelpText),
  new Page('CmkInlineValidation', UclCmkInlineValidation),
  new Page('CmkLoading', UclCmkLoading),
  new Page('CmkPerfometer', UclCmkPerfometer),
  new Page('CmkPopup', UclCmkPopup),
  new Page('CmkPopupDialog', UclCmkPopupDialog),
  new Page('CmkProgressbar', UclCmkProgressbar),
  new Page('CmkSkeleton', UclCmkSkeleton),
  new Page('CmkTooltip', UclCmkTooltip)
]
export const roots = [
  new Folder('Foundations', foundationsPages, true),
  new Folder(
    'Components',
    [
      new Folder('Basic elements', basicElementsPages, true),
      new Folder('Content organization', contentOrganizationPages, true),
      new Folder('Form elements', formElementsPages),
      new Folder('Foundation elements', foundationElementsPages),
      new Folder('Graphics', graphicsPages),
      new Folder('Navigation', navigationPages),
      new Folder('System feedback', systemFeedbackPages)
    ],
    true
  ),
  new Folder('Developer Playground', [
    new Folder('Form Spec Elements', formSpecPages),
    new Folder('I18n', i18nPages),
    new Folder('Two Factor Authentication', twoFactorAuthPages)
  ])
]
