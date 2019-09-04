# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_mem'


info = [['cache', '41316352'],
        ['rss', '79687680'],
        ['rss_huge', '8388608'],
        ['mapped_file', '5976064'],
        ['swap', '0'],
        ['pgpgin', '7294455'],
        ['pgpgout', '7267468'],
        ['pgfault', '39514980'],
        ['pgmajfault', '111'],
        ['inactive_anon', '0'],
        ['active_anon', '79642624'],
        ['inactive_file', '28147712'],
        ['active_file', '13168640'],
        ['unevictable', '0'],
        ['hierarchical_memory_limit', '9223372036854771712'],
        ['hierarchical_memsw_limit', '9223372036854771712'],
        ['total_cache', '41316352'],
        ['total_rss', '79687680'],
        ['total_rss_huge', '8388608'],
        ['total_mapped_file', '5976064'],
        ['total_swap', '0'],
        ['total_pgpgin', '7294455'],
        ['total_pgpgout', '7267468'],
        ['total_pgfault', '39514980'],
        ['total_pgmajfault', '111'],
        ['total_inactive_anon', '0'],
        ['total_active_anon', '79642624'],
        ['total_inactive_file', '28147712'],
        ['total_active_file', '13168640'],
        ['total_unevictable', '0'],
        ['usage_in_bytes', '121810944'],
        ['limit_in_bytes', '9223372036854771712'],
        ['MemTotal:', '65660592', 'kB']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'levels': (150.0, 200.0)},
                [(0,
                  '76.77 MB used (this is 0.1% of 62.62 GB RAM)',
                  [('ramused', 76.765625, None, None, 0, 64121.671875),
                   ('swapused', 0, None, None, 0, 0),
                   ('memused', 76.765625, 96182, 128243, 0, 64121.671875)])])]}