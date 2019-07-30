# -*- encoding: utf-8
# yapf: disable


checkname = 'netapp_api_psu'


info = [[u'power-supply-list 0',
         u'is-auto-power-reset-enabled false',
         u'power-supply-part-no 114-00065+A2',
         u'power-supply-serial-no XXT133880145',
         u'power-supply-is-error false',
         u'power-supply-firmware-revision 020F',
         u'power-supply-type 9C',
         u'power-supply-swap-count 0',
         u'power-supply-element-number 1'],
        [u'power-supply-list 0',
         u'is-auto-power-reset-enabled false',
         u'power-supply-part-no 114-00065+A2',
         u'power-supply-serial-no XXT133880140',
         u'power-supply-is-error true',
         u'power-supply-firmware-revision 020F',
         u'power-supply-type 9C',
         u'power-supply-swap-count 0',
         u'power-supply-element-number 2']]


discovery = {'': [], 'summary': [('Summary', {})]}


checks = {'summary': [('Summary',
                       {},
                       [(0, '2 power supply units in total', []),
                        (2, u'1 power supply unit in error state (0/2)', [])])]}


mock_host_conf_merged = {'': {'mode': 'summary'}, 'summary': {'mode': 'summary'}}