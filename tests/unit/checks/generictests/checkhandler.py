import copy

import cmk_base.config as config
import cmk_base.check_api as check_api


class CheckHandler(object):
    """Collect the info on all checks"""
    def __init__(self):
        config.load_all_checks(check_api.get_check_api_context)
        self.info = copy.deepcopy(config.check_info)
        self.cache = {}

    def get_applicables(self, checkname):
        """get a list of names of all (sub)checks that apply"""
        if checkname in self.cache:
            return self.cache[checkname]
        found = [s for s in self.info.keys() if s.split('.')[0] == checkname]
        return self.cache.setdefault(checkname, found)


checkhandler = CheckHandler()
