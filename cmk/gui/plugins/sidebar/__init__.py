import os
import glob
import abc

modules = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
__all__ = [ os.path.basename(f)[:-3] for f in modules if f not in [ "__init__.py", "utils.py" ] ]


class SidebarSnapin(object):
    metaclass = abc.ABCMeta

    @abc.abstractmethod
    def title(self):
        raise NotImplementedError()


    def description(self):
        return ""


    @abc.abstractmethod
    def show(self):
        raise NotImplementedError()


    def refresh_regularly(self):
        return False


    def refresh_on_restart(self):
        return False


    def allowed_roles(self):
        return [ "admin", "user", "guest" ]


    def styles(self):
        return None


    def page_handlers(self):
        return {}

from . import *
