#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function
import errno
import os
import sys
import time
import pprint
import pytest
import signal
import threading
import Queue
import traceback
from urlparse import urlsplit, parse_qsl, urlunsplit, urljoin
from urllib import urlencode
from bs4 import BeautifulSoup
from testlib import web

from testlib import CMKWebSession


class InvalidUrl(Exception):
    pass


class Url(object):
    def __init__(self, url, orig_url=None, referer_url=None):
        self.url = url
        self.orig_url = orig_url
        self.referer_url = referer_url

    def __hash__(self):
        return hash(self.url)

    # Strip host and site prefix
    def neutral_url(self):
        return "check_mk/" + self.url.split("/check_mk/", 1)[1]

    # Strip proto and host
    def url_without_host(self):
        parsed = list(urlsplit(self.url))
        parsed[0] = None
        parsed[1] = None
        return urlunsplit(parsed)


class Worker(threading.Thread):
    def __init__(self, num, crawler):
        super(Worker, self).__init__()
        self.name = "worker-%d" % num
        self.crawler = crawler
        self.daemon = True
        self.terminate = False
        self.idle = True

        self.client = CMKWebSession(self.crawler.site)
        self.client.login()
        self.client.set_language("en")

    def run(self):
        while not self.terminate:
            try:
                while not self.terminate:
                    url = self.crawler.todo.get(block=False)
                    self.idle = False
                    try:
                        self.visit_url(url)
                    except Exception as e:
                        self.error(url, "Failed to visit: %s\n%s" % (e, traceback.format_exc()))
                    self.crawler.todo.task_done()
            except Queue.Empty:
                self.idle = True
                time.sleep(0.5)

    def stop(self):
        self.terminate = True

    def visit_url(self, url):
        if url.url in self.crawler.visited:
            print("Already visited: %s" % url.url)
            return
        self.crawler.visited.append(url.url)

        #print("%s - Visiting #%d (todo %d): %s" %
        #    (self.name, len(self.crawler.visited), self.crawler.todo.qsize(), url.url))

        started = time.time()
        try:
            #print "FETCH", url.url_without_host()
            response = self.client.get(url.url_without_host())
        except AssertionError as e:
            if "This view can only be used in mobile mode" in "%s" % e:
                print("Skipping mobile mode view checking")
                return
            else:
                raise
        duration = time.time() - started

        self.update_stats(url, duration, len(response.content))

        content_type = response.headers.get('content-type')
        #print self.name, content_type, len(response.text)

        if content_type.startswith("text/html"):
            self.check_response(url, response)
        elif content_type.startswith("text/plain"):
            pass  # no specific test
        elif content_type.startswith("text/csv"):
            pass  # no specific test
        elif content_type in ["image/png", "image/gif"]:
            pass  # no specific test
        elif content_type in ["application/pdf"]:
            pass  # no specific test
        elif content_type in [
                "application/x-rpm",
                "application/x-deb",
                "application/x-debian-package",
                "application/x-gzip",
                "application/x-msdos-program",
                "application/x-msi",
                "application/x-tgz",
                "application/x-redhat-package-manager",
                "application/x-pkg",
                "text/x-chdr",
                "text/x-c++src",
                "text/x-sh",
        ]:
            pass  # no specific test
        else:
            self.error(url, "Unknown content type: %s" % (content_type))
            return

    def update_stats(self, url, duration, content_size):
        stats = self.crawler.stats.setdefault(url.neutral_url(), {
            "first_duration": duration,
            "first_content_size": content_size,
        })

        avg_duration = (duration + stats.get("avg_duration", duration)) / 2.0
        avg_content_size = (content_size + stats.get("avg_content_size", content_size)) / 2.0

        stats.update({
            "orig_url": url.orig_url,
            "referer_url": url.referer_url,
            "num_visited": stats.get("num_visited", 0) + 1,
            "last_duration": duration,
            "last_content_size": content_size,
            "avg_duration": avg_duration,
            "avg_content_size": avg_content_size,
        })

    def error(self, url, s):
        s = "[%s - found on %s] %s" % (url.url, url.referer_url, s)
        self.crawler.error(s)

    def check_response(self, url, response):
        soup = BeautifulSoup(response.text, "lxml")

        # The referenced resources (images, stylesheets, javascript files) are checked by
        # the generic web client handler. This only needs to reaslize the crawling.
        self.check_content(url, response, soup)
        self.check_links(url, soup)
        self.check_frames(url, soup)
        self.check_iframes(url, soup)

    def check_content(self, url, response, soup):
        ignore_texts = [
            "This view can only be used in mobile mode.",
        ]

        for element in soup.select("div.error"):
            inner_html = "%s" % element

            skip = False
            for ignore_text in ignore_texts:
                if ignore_text in inner_html:
                    skip = True
                    break

            if not skip:
                self.error(url, "Found error: %s" % (element))

    def check_frames(self, url, soup):
        self.check_referenced(url, soup, "frame", "src")

    def check_iframes(self, url, soup):
        self.check_referenced(url, soup, "iframe", "src")

    def check_links(self, url, soup):
        self.check_referenced(url, soup, "a", "href")

    def check_referenced(self, referer_url, soup, tag, attr):
        elements = soup.find_all(tag)

        for element in elements:
            orig_url = element.get(attr)
            url = self.normalize_url(self.crawler.site.internal_url, orig_url)

            if url is None:
                continue

            try:
                self.verify_is_valid_url(url)
            except InvalidUrl as e:
                #print self.name, "skip invalid", url, e
                self.crawler.skipped.add(url)
                continue

            # Ensure that this url has not been crawled yet
            crawl_it = False
            with self.crawler.handled_lock:
                if url not in self.crawler.handled:
                    crawl_it = True
                    self.crawler.handled.add(url)

            if crawl_it:
                #file("/tmp/todo", "a").write("%s (%s)\n" % (url, referer_url.url))
                self.crawler.todo.put(Url(url, orig_url=orig_url, referer_url=referer_url.url))

    def verify_is_valid_url(self, url):
        parsed = urlsplit(url)

        if parsed.scheme != "http":
            raise InvalidUrl("invalid scheme: %r" % (parsed,))

        # skip external urls
        if url.startswith("http://") and not url.startswith(self.crawler.site.internal_url):
            raise InvalidUrl("Skipping external URL: %s" % url)

        # skip non check_mk urls
        if not parsed.path.startswith("/%s/check_mk" % self.crawler.site.id) \
           or "../pnp4nagios/" in parsed.path \
           or "../nagvis/" in parsed.path \
           or "../nagios/" in parsed.path:
            raise InvalidUrl("Skipping non Check_MK URL: %s %s" % (url, parsed))

        # skip current url with link to index
        if "index.py?start_url=" in url:
            raise InvalidUrl("Skipping link to index with current URL: %s" % url)

        if "logout.py" in url:
            raise InvalidUrl("Skipping logout URL: %s" % url)

        if "_transid=" in url:
            raise InvalidUrl("Skipping action URL: %s" % url)

        if "selection=" in url:
            raise InvalidUrl("Skipping selection URL: %s" % url)

        # TODO: Remove this exclude when ModeCheckManPage works without an
        # automation call. Currently we have to use such a call to enrich the
        # man page with some additional info from config.check_info, see
        # AutomationGetCheckManPage.
        if "mode=check_manpage" in url and "wato.py" in url:
            raise InvalidUrl("Skipping man page URL: %s" % url)

        # Don't follow filled in filter form views
        if "view.py" in url and "filled_in=filter" in url:
            raise InvalidUrl("Skipping filled in filter URL: %s" % url)

        # Don't follow the view editor
        if "edit_view.py" in url:
            raise InvalidUrl("Skipping view editor URL: %s" % url)

        # Skip agent download files
        if parsed.path.startswith("/%s/check_mk/agents/" % self.crawler.site.id):
            raise InvalidUrl("Skipping agent download file: %s" % url)

    def normalize_url(self, base_url, url):
        url = urljoin(base_url, url.rstrip("#"))
        parsed = list(urlsplit(url))
        parsed[3] = urlencode(sorted(parse_qsl(parsed[3], keep_blank_values=True)))
        return urlunsplit(parsed)


class SetQueue(Queue.Queue):
    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


class TestCrawler(object):
    @pytest.mark.type("gui_crawl")
    def test_crawl(self, site):
        self.stats = {}
        self.todo = SetQueue()
        self.started = time.time()
        self.visited = []
        self.skipped = set()

        # Contains all already seen and somehow handled URLs. Something like the
        # summary of self.todo and self.handled but todo contains Url() objects.
        self.handled = set()
        self.handled_lock = threading.Lock()

        self.errors = []
        self.site = site
        self.num_workers = 10

        self.load_stats()

        self.todo.put(Url(site.internal_url))
        self.handled.add(site.internal_url)

        self.crawl()

        self.report()

    def var_dir(self):
        return self.site.path("var/log")

    def stats_file(self):
        return self.var_dir() + "/crawl.stats"

    def report_file(self):
        return self.var_dir() + "/crawl.report"

    def web_log_file(self):
        return self.var_dir() + "/crawl-web.log"

    def apache_error_log_file(self):
        return self.var_dir() + "/crawl-apache_error_log.log"

    def load_stats(self):
        try:
            self.stats = eval(file(self.stats_file()).read())
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existing files are OK
            else:
                raise

    def save_stats(self):
        file(self.stats_file() + ".tmp", "w").write(pprint.pformat(self.stats) + "\n")
        os.rename(self.stats_file() + ".tmp", self.stats_file())

    def update_total_stats(self, finished):
        stats = self.stats.setdefault("_TOTAL_", {})

        stats["last_num_visited"] = len(self.visited)
        stats["last_duration"] = time.time() - self.started
        stats["last_errors"] = self.errors
        stats["last_finished"] = finished

        if finished:
            if stats.get("last_finished_num_visited", 0) > 0:
                perc = float(stats["last_num_visited"]) * 100 / stats["last_finished_num_visited"]
                if perc < 80.0:
                    self.error(
                        "Finished and walked %d URLs, previous run walked %d URLs. That "
                        "is %0.2f %% of the previous run. Something seems to be wrong." %
                        (stats["last_num_visited"], stats["last_finished_num_visited"], perc))

            stats["last_finished_num_visited"] = stats["last_num_visited"]
            stats["last_finished_duration"] = stats["last_duration"]
            stats["last_finished_errors"] = stats["last_errors"]

    def report(self):
        with file(self.report_file() + ".tmp", "w") as f:
            f.write("Skipped URLs:\n")
            for skipped_url in sorted(self.skipped):
                f.write("  %s\n" % skipped_url)
            f.write("\n")

            f.write("Visited URLs:\n")
            for visited_url in self.visited:
                f.write("  %s\n" % visited_url)
            f.write("\n")

            if self.errors:
                f.write("Crawled %d URLs in %d seconds. Failures:\n%s\n" %
                        (len(self.visited), time.time() - self.started, "\n".join(self.errors)))

        # Copy the previous file for analysis
        #if os.path.exists(self.report_file()):
        #    open(self.report_file()+".old", "w").write(open(self.report_file()).read())

        os.rename(self.report_file() + ".tmp", self.report_file())

        if self.errors:
            for site_path, test_path in [
                ("var/log/web.log", self.web_log_file()),
                ("var/log/apache/error_log", self.apache_error_log_file()),
            ]:
                if self.site.file_exists(site_path):
                    open(test_path + ".tmp", "w").write(self.site.read_file(site_path))
                    os.rename(test_path + ".tmp", test_path)

            pytest.fail("Crawled %d URLs in %d seconds. Failures:\n%s" %
                        (len(self.visited), time.time() - self.started, "\n".join(self.errors)))

    def error(self, msg):
        print(msg)
        self.errors.append(msg)

    def crawl(self):
        finished = False
        workers = []
        try:
            for i in range(self.num_workers):
                t = Worker(i, self)
                t.start()
                workers.append(t)

            start = time.time()
            last_tick, last_num_visited = time.time(), 0
            while True:
                now = time.time()
                duration = max(now - start, 1)
                num_visited = len(self.visited)
                num_idle = len([w for w in workers if w.idle])
                rate_runtime = num_visited / duration

                if now > last_tick and num_visited > last_num_visited:
                    rate_tick = (num_visited - last_num_visited) / (now - last_tick)
                else:
                    rate_tick = 0

                last_tick = now
                last_num_visited = num_visited

                print("Workers: %d (Idle: %d), Rate: %0.2f/s (1sec: %0.2f/s), Duration: %d sec, "
                      "Visited: %s, Todo: %d" %
                      (self.num_workers, num_idle, rate_runtime, rate_tick, duration, num_visited,
                       self.todo.qsize()))

                if self.todo.qsize() == 0 and all([w.idle for w in workers]):
                    break
                else:
                    time.sleep(1)

            finished = True
        except KeyboardInterrupt:
            for t in workers:
                t.stop()
            print("Waiting for workers to finish...")
        finally:
            self.update_total_stats(finished)
            self.save_stats()
