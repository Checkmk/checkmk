/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import { pages as formSpecPages } from '../form'
import UclCmkBadge from './basic-elements/CmkBadge/UclCmkBadge.vue'
import UclCmkButton from './basic-elements/CmkButton/UclCmkButton.vue'
import UclCmkChip from './basic-elements/CmkChip/UclCmkChip.vue'
import UclCmkCode from './basic-elements/CmkCode/UclCmkCode.vue'
import UclCmkColorPicker from './basic-elements/CmkColorPicker/UclCmkColorPicker.vue'
import UclCmkIconButton from './basic-elements/CmkIconButton/UclCmkIconButton.vue'
import UclCmkInlineButton from './basic-elements/CmkInlineButton/UclCmkInlineButton.vue'
import UclCmkSwitch from './basic-elements/CmkSwitch/UclCmkSwitch.vue'
import UclCmkTag from './basic-elements/CmkTag/UclCmkTag.vue'
import UclCmkAccordion from './content-organization/CmkAccordion/UclCmkAccordion.vue'
import UclCmkAccordionStepPanel from './content-organization/CmkAccordionStepPanel/UclAccordionCmkStepPanel.vue'
import UclCmkCatalogPanel from './content-organization/CmkCatalogPanel/UclCmkCatalogPanel.vue'
import UclCmkCollapsible from './content-organization/CmkCollapsible/UclCmkCollapsible.vue'
import UclCmkScrollContainer from './content-organization/CmkScrollContainer/UclCmkScrollContainer.vue'
import UclCmkSlideIn from './content-organization/CmkSlideIn/UclCmkSlideIn.vue'
import UclCmkSlideInDialog from './content-organization/CmkSlideInDialog/UclCmkSlideInDialog.vue'
import UclCmkTabs from './content-organization/CmkTabs/UclCmkTabs.vue'
import UclCmkWizard from './content-organization/CmkWizard/UclCmkWizard.vue'
import UclTwoFactorAuth from './content-organization/TwoFactorAuthentication/UclTwoFactorAuthentication.vue'
import UclCmkCheckbox from './form-elements/CmkCheckbox/UclCmkCheckbox.vue'
import UclCmkDateTimePicker from './form-elements/CmkDateTimePicker/UclCmkDateTimePicker.vue'
import UclCmkDropdown from './form-elements/CmkDropdown/UclCmkDropdown.vue'
import UclCmkDualList from './form-elements/CmkDualList/UclCmkDualList.vue'
import UclCmkInput from './form-elements/CmkInput/UclCmkInput.vue'
import UclCmkList from './form-elements/CmkList/UclCmkList.vue'
import UclCmkToggleButtonGroup from './form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroup.vue'
import UclConfigurationEntityDropdown from './form-elements/ConfigurationEntityDropdown/UclConfigurationEntityDropdown.vue'
import UclCmkHtml from './foundation-elements/CmkHtml/UclCmkHtml.vue'
import UclCmkIcon from './foundation-elements/CmkIcon/UclCmkIcon.vue'
import UclCmkIconEmblem from './foundation-elements/CmkIcon/UclCmkIconEmblem.vue'
import UclCmkMultitoneIcon from './foundation-elements/CmkIcon/UclCmkMultitoneIcon.vue'
import UclCmkIndent from './foundation-elements/CmkIndent/UclCmkIndent.vue'
import UclCmkKeyboardKey from './foundation-elements/CmkKeyboardKey/UclCmkKeyboardKey.vue'
import UclCmkLabelRequired from './foundation-elements/CmkLabelRequired/UclCmkLabelRequired.vue'
import UclCmkSpace from './foundation-elements/CmkSpace/UclCmkSpace.vue'
import UclCmkZebra from './foundation-elements/CmkZebra/UclCmkZebra.vue'
import UclCmkHeading from './foundation-elements/typography/UclCmkHeading.vue'
import UclCmkParagraph from './foundation-elements/typography/UclCmkParagraph.vue'
import UclI18n from './foundation-elements/typography/UclI18n.vue'
import UclCmkLinkCard from './navigation/CmkLinkCard/UclCmkLinkCard.vue'
import UclCmkAlertBox from './system-feedback/CmkAlertBox/UclCmkAlertBox.vue'
import UclCmkCopyButton from './system-feedback/CmkCopy/UclCmkCopyButton.vue'
import UclCmkCopyIcon from './system-feedback/CmkCopy/UclCmkCopyIcon.vue'
import UclCmkDialog from './system-feedback/CmkDialog/UclCmkDialog.vue'
import UclCmkInlineValidation from './system-feedback/CmkInlineValidation/UclCmkInlineValidation.vue'
import UclCmkLoading from './system-feedback/CmkLoading/UclCmkLoading.vue'
import UclCmkPerfometer from './system-feedback/CmkPerfometer/UclCmkPerfometer.vue'
import UclCmkPopupDialog from './system-feedback/CmkPopupDialog/UclCmkPopupDialog.vue'
import UclCmkProgressbar from './system-feedback/CmkProgressbar/UclCmkProgressbar.vue'
import UclCmkSkeleton from './system-feedback/CmkSkeleton/UclCmkSkeleton.vue'
import UclCmkTooltip from './system-feedback/CmkTooltip/UclCmkTooltip.vue'
import UclErrorBoundary from './system-feedback/ErrorBoundary/UclErrorBoundary.vue'
import UclHelp from './system-feedback/Help/UclHelp.vue'

const basicElementsPages = [
  new Page('CmkBadge', UclCmkBadge),
  new Page('CmkButton', UclCmkButton),
  new Page('CmkIconButton', UclCmkIconButton),
  new Page('CmkInlineButton', UclCmkInlineButton),
  new Page('CmkChip', UclCmkChip),
  new Page('CmkCode', UclCmkCode),
  new Page('CmkColorPicker', UclCmkColorPicker),
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
  new Page('CmkWizard', UclCmkWizard),
  new Page('TwoFactorAuth', UclTwoFactorAuth)
]

const formElementsPages = [
  new Page('CmkCheckbox', UclCmkCheckbox),
  new Page('CmkConfigurationEntityDropdown', UclConfigurationEntityDropdown),
  new Page('CmkDateTimePicker', UclCmkDateTimePicker),
  new Page('CmkDropdown', UclCmkDropdown),
  new Page('CmkDualList', UclCmkDualList),
  new Page('CmkInput', UclCmkInput),
  new Page('CmkList', UclCmkList),
  new Page('CmkToggleButtonGroup', UclCmkToggleButtonGroup)
]

const foundationElementsPages = [
  new Page('CmkIcon', UclCmkIcon),
  new Page('CmkIconEmblem', UclCmkIconEmblem),
  new Page('CmkMultitoneIcon', UclCmkMultitoneIcon),
  new Page('CmkHeading', UclCmkHeading),
  new Page('CmkParagraph', UclCmkParagraph),
  new Page('i18n', UclI18n),
  new Page('CmkHtml', UclCmkHtml),
  new Page('CmkIndent', UclCmkIndent),
  new Page('CmkKeyboardKey', UclCmkKeyboardKey),
  new Page('CmkLabelRequired', UclCmkLabelRequired),
  new Page('CmkSpace', UclCmkSpace),
  new Page('CmkZebra', UclCmkZebra)
]

const navigationPages = [new Page('CmkLinkCard', UclCmkLinkCard)]

const systemFeedbackPages = [
  new Page('CmkAlertBox', UclCmkAlertBox),
  new Page('CmkCopy (Button)', UclCmkCopyButton),
  new Page('CmkCopy (Icon)', UclCmkCopyIcon),
  new Page('CmkDialog', UclCmkDialog),
  new Page('CmkErrorBoundary', UclErrorBoundary),
  new Page('CmkHelpText', UclHelp),
  new Page('CmkInlineValidation', UclCmkInlineValidation),
  new Page('CmkLoading', UclCmkLoading),
  new Page('CmkPerfometer', UclCmkPerfometer),
  new Page('CmkPopupDialog', UclCmkPopupDialog),
  new Page('CmkProgressbar', UclCmkProgressbar),
  new Page('CmkSkeleton', UclCmkSkeleton),
  new Page('CmkTooltip', UclCmkTooltip)
]
export const roots = [
  new Folder(
    'Components',
    [
      new Folder('Basic elements', basicElementsPages, true),
      new Folder('Content organization', contentOrganizationPages, true),
      new Folder('Form elements', formElementsPages),
      new Folder('Foundation elements', foundationElementsPages),
      new Folder('Navigation', navigationPages),
      new Folder('System feedback', systemFeedbackPages)
    ],
    true
  ),
  new Folder('Developer Playground', [new Folder('Form Spec Elements', formSpecPages)])
]
