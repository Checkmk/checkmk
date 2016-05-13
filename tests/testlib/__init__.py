#!/usr/bin/env python
# encoding: utf-8

import os
import time
import pytest
import platform
import re
import requests
import pipes
import subprocess


def repo_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def cmk_path():
    return repo_path()


def cmc_path():
    return os.path.realpath(repo_path() + "/../cmc")


# Directory for persisting variable data produced by tests
def var_dir():
    if "WORKSPACE" in os.environ:
        base_dir = os.environ["WORKSPACE"]
    else:
        base_dir = repo_path() + "/tests"

    return base_dir + "/var"


def omd(cmd):
    return os.system(" ".join(["sudo", "/usr/bin/omd"] + cmd + [">/dev/null"])) >> 8


# It's ok to make it currently only work on debian based distros
class CMKVersion(object):
    DEFAULT = "default"
    DAILY   = "daily"

    CEE   = "cee"
    CRE   = "cre"

    def __init__(self, version, edition):
        self.set_version(version)
        self.edition_short = edition

        self._credentials = ("d-vonheute", "lOBFsgAH")


    def get_default_version(self):
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]


    def set_version(self, version):
        if version == CMKVersion.DAILY:
            self.version = time.strftime("%Y.%m.%d")

        elif version == CMKVersion.DEFAULT:
            self.version = self.get_default_version()

        else:
            self.version = version


    def edition(self):
        return self.edition_short == CMKVersion.CRE and "raw" or "enterprise"


    def _needed_distro(self):
        return os.popen("lsb_release -a 2>/dev/null | grep Codename | awk '{print $2}'").read().strip()


    def _needed_architecture(self):
        return platform.architecture()[0] == "64bit" and "amd64" or "i386"


    def package_name(self):
        return "check-mk-%s-%s_0.%s_%s.deb" % \
		(self.edition(), self.version, self._needed_distro(), self._needed_architecture())


    def package_url(self):
        return "https://mathias-kettner.de/support/%s/%s" % (self.version, self.package_name())


    def version_directory(self):
        return "%s.%s" % (self.version, self.edition_short)


    def version_path(self):
        return "/omd/versions/%s" % self.version_directory()


    def is_installed(self):
        return os.path.exists(self.version_path())


    def install(self):
        temp_package_path = "/tmp/%s" % self.package_name()

        print(self.package_url())
        response = requests.get(self.package_url(), auth=self._credentials, verify=False)
        if response.status_code != 200:
            raise Exception("Failed to load package: %s" % self.package_url())
        file(temp_package_path, "w").write(response.content)

        cmd = "sudo /usr/bin/gdebi --non-interactive %s" % temp_package_path
        print(cmd)
        if os.system(cmd) >> 8 != 0:
            raise Exception("Failed to install package: %s" % temp_package_path)

        assert self.is_installed()



class Site(object):
    def __init__(self, site_id, reuse=True, version=CMKVersion.DEFAULT,
                 edition=CMKVersion.CEE):
        assert site_id
        self.id      = site_id
        self.root    = "/omd/sites/%s" % self.id
        self.version = CMKVersion(version, edition)

        self.reuse   = reuse
        self.url     = "http://127.0.0.1/%s/check_mk/" % self.id


    def execute(self, cmd, *args, **kwargs):
        cmd = [ "sudo", "su", "-l", self.id,
                "-c", pipes.quote(" ".join([ pipes.quote(p) for p in cmd ])) ]
        cmd_txt = " ".join(cmd)
        return subprocess.Popen(cmd_txt, shell=True, *args, **kwargs)


    def cleanup_if_wrong_version(self):
        if not self.exists():
            return

        if self.current_version_directory() == self.version.version_directory():
            return

        # Now cleanup!
        self.rm()


    def current_version_directory(self):
        return os.path.split(os.readlink("/omd/sites/%s/version" % self.id))[-1]


    def create(self):
        if not self.version.is_installed():
            self.version.install()

        if not self.reuse and self.exists():
            raise Exception("The site %s already exists." % self.id)

        if not self.exists():
            assert omd(["-V", self.version.version_directory(), "create", self.id]) == 0
            assert os.path.exists("/omd/sites/%s" % self.id)


    def rm_if_not_reusing(self):
        if not self.reuse:
            self.rm()


    def rm(self):
        assert omd(["-f", "rm", "--kill", self.id]) == 0


    def start(self):
        if not self.is_running():
            assert omd(["start", self.id]) == 0
            assert self.is_running()


    def exists(self):
        return os.path.exists("/omd/sites/%s" % self.id)


    def is_running(self):
        return omd(["status", "--bare", self.id]) == 0



@pytest.fixture(scope="session")
def site(request):
    def site_id():
        site_id = os.environ.get("SITE")
        if site_id == None:
            site_id = file(repo_path() + "/.site").read().strip()

        return site_id

    def site_version():
        version = os.environ.get("VERSION", CMKVersion.DEFAULT)
        return version

    site = Site(site_id=site_id(), version=site_version())
    site.cleanup_if_wrong_version()
    site.create()
    site.start()

    def fin():
        site.rm_if_not_reusing()
    request.addfinalizer(fin)

    return site


class WebSession(requests.Session):
    transids = {}

    def __init__(self, site):
        self.site = site
        self.url  = site.url

        super(WebSession, self).__init__()


    def get(self, *args, **kwargs):
        response = super(WebSession, self).get(*args, **kwargs)
        self._handle_http_response(response)
        return response


    def post(self, url, *args, **kwargs):
	if kwargs.get("add_transid"):
            del kwargs["add_transid"]

            transids = WebSession.transids.get(self.site.id, [])
            if not transids:
                raise Exception('Tried to add a transid, but none available at the moment')

            if "?" in url:
                url += "&"
            else:
                url += "?"
            url += "_transid=" + transids.pop()

        response = super(WebSession, self).post(url, *args, **kwargs)
        self._handle_http_response(response)
        return response


    def _handle_http_response(self, response):
        assert "Content-Type" in response.headers

        def get_mime_type(response):
            return response.headers["Content-Type"].split(";", 1)[0]

        mime_type = get_mime_type(response)

        assert response.status_code == 200

        if mime_type == "text/html":
            self._check_html_page(response)


    def _check_html_page(self, response):
        self._extract_transids(response.text)
        self._find_errors(response.text)
        # TODO: Check resources (css, js, images)


    def _extract_transids(self, body):
        # Extract transids from the pages to be used in later actions
        # issued by the tests
        matches = re.findall('name="_transid" value="([^"]+)"', body)
        matches += re.findall('_transid=([0-9/]+)', body)
        for match in matches:
            transids = WebSession.transids.setdefault(self.site.id, [])
            transids.append(match)


    def _find_errors(self, body):
        matches = re.search('<div class=error>(.*?)</div>', body, re.M | re.DOTALL)
        assert not matches, "Found error message: %s" % matches.groups()


    def login(self, username="omdadmin", password="omd"):
        login_page = self.get(self.url).text
        assert "_username" in login_page, "_username not found on login page - page broken?"
        assert "_password" in login_page
        assert "_login" in login_page

        r = self.post(self.url + "login.py", {
            "filled_in" : "login",
            "_username" : username,
            "_password" : password,
            "_login"    : "Login",
        })
        auth_cookie = r.cookies.get("auth_%s" % self.site.id)
        assert auth_cookie.startswith("%s:" % username)

        assert "side.py" in r.text
        assert "dashboard.py" in r.text


    def set_language(self, lang):
        lang = "" if lang == "en" else lang

        profile_page = self.get(self.url + "user_profile.py").text
        assert "name=\"language\"" in profile_page
        assert "value=\""+lang+"\"" in profile_page

        r = self.post(self.url + "user_profile.py", {
            "filled_in" : "profile",
            "_set_lang" : "on",
            "language"  : lang,
            "_save"     : "Save",
        }, add_transid=True)

        if lang == "":
            assert "Successfully updated" in r.text
        else:
            assert "Benutzerprofil erfolgreich aktualisiert" in r.text


    def logout(self):
        r = self.get(self.url + "logout.py")
        assert "action=\"login.py\"" in r.text



@pytest.fixture(scope="module")
def web(site):
    web = WebSession(site)
    web.login()
    web.set_language("en")
    return web
