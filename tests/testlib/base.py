import cmk_base.config as config


class Scenario(object):
    """Helper class to modify the Check_MK base configuration for unit tests"""

    def __init__(self, site_id="unit"):
        super(Scenario, self).__init__()
        self.config = {
            "distributed_wato_site": site_id,
            "all_hosts": [],
            "host_paths": {},
            "host_tags": {},
            "clusters": {},
        }
        self.config_cache = config.get_config_cache()

    def add_host(self, hostname, tags=None, folder="/"):
        if tags is None:
            tags = []

        self.config["all_hosts"].append("%s|%s" % (hostname, "|".join(tags)))
        self.config["host_paths"][hostname] = folder
        #self.config["host_tags"][hostname] = tags
        return self

    def add_cluster(self, hostname, tags=None, folder="/", nodes=None):
        if tags is None:
            tags = []
        if nodes is None:
            nodes = []
        name_with_tags = "%s|%s" % (hostname, "|".join(tags))
        self.config["clusters"][name_with_tags] = nodes
        self.config["host_paths"][hostname] = folder
        #self.config["host_tags"][hostname] = tags
        return self

    def set_option(self, varname, option):
        self.config[varname] = option
        return self

    def set_ruleset(self, varname, ruleset):
        self.config[varname] = ruleset
        return self

    def apply(self, monkeypatch):
        for key, value in self.config.items():
            monkeypatch.setattr(config, key, value)

        self.config_cache = config.get_config_cache()
        self.config_cache.initialize()
        return self.config_cache
