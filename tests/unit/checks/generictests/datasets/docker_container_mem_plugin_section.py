# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_mem'


info = [['@docker_version_info',
         '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
        ['{"usage": 4034560, "limit": 16690180096, "stats": {"unevictable": 0, "total_inactive_file": 0, "total_rss_huge": 0, "hierarchical_memsw_limit": 0, "total_cache": 0, "total_mapped_file": 0, "mapped_file": 0, "pgfault": 41101, "total_writeback": 0, "hierarchical_memory_limit": 9223372036854771712, "total_active_file": 0, "rss_huge": 0, "cache": 0, "active_anon": 860160, "pgmajfault": 0, "total_pgpgout": 29090, "writeback": 0, "pgpgout": 29090, "total_active_anon": 860160, "total_unevictable": 0, "total_pgfault": 41101, "total_pgmajfault": 0, "total_inactive_anon": 0, "inactive_file": 0, "pgpgin": 29300, "total_dirty": 0, "total_pgpgin": 29300, "rss": 860160, "active_file": 0, "inactive_anon": 0, "dirty": 0, "total_rss": 860160}, "max_usage": 7208960}']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'levels': (150.0, 200.0)},
                [(0,
                  '3.85 MB used (this is 0.0% of 15.54 GB RAM)',
                  [('ramused', 3.84765625, None, None, 0, 15916.99609375),
                   ('swapused', 0, None, None, 0, 0),
                   ('memused', 3.84765625, 23875, 31833, 0, 15916.99609375)])])]}