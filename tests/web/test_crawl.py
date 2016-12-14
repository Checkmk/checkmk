#!/usr/bin/env python
# encoding: utf-8

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
from testlib import web, var_dir


class Url(object):
    def __init__(self, url, orig_url=None, referer_url=None):
        self.url         = url
        self.orig_url    = orig_url
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
        self.name      = "worker-%d" % num
        self.crawler   = crawler
        self.daemon    = True
        self.terminate = False
        self.idle      = True

    def run(self):
        while not self.terminate:
            try:
                while not self.terminate:
                    url = self.crawler.todo.get(block=False)
                    self.idle = False
                    try:
                        self.visit_url(url)
                    except Exception, e:
                        self.error(url, "Failed to visit: %s\n%s" %
                                     (e, traceback.format_exc()))
                    self.idle = True
                    self.crawler.todo.task_done()
            except Queue.Empty:
                time.sleep(0.5)


    def stop(self):
        self.terminate = True


    def visit_url(self, url):
        if url.url in self.crawler.visited:
            #print("Already visited: %s" % url.url)
            return
        self.crawler.visited.append(url.url)

        #print("%s - Visiting #%d (todo %d): %s" %
        #    (self.name, len(self.crawler.visited), self.crawler.todo.qsize(), url.url))

        started = time.time()
        try:
            #print url.url_without_host()
            response = self.crawler.client.get(url.url_without_host())
        except AssertionError, e:
            if "This view can only be used in mobile mode" in "%s" % e:
                return
            else:
                raise
        duration = time.time() - started

        self.update_stats(url, duration, len(response.content))

        content_type = response.headers.get('content-type')
        if content_type.startswith("text/html"):
            self.check_response(url, response)
        elif content_type.startswith("text/plain"):
            pass # no specific test
        elif content_type.startswith("text/csv"):
            pass # no specific test
        elif content_type in [ "image/png", "image/gif" ]:
            pass # no specific test
        elif content_type in [ "application/pdf" ]:
            pass # no specific test
        elif content_type in [ "application/x-rpm", "application/x-deb", "application/x-debian-package",
                               "application/x-gzip", "application/x-msdos-program", "application/x-msi",
                               "application/x-tgz", "application/x-redhat-package-manager",
                               "text/x-chdr", "text/x-c++src", "text/x-sh", ]:
            pass # no specific test
        else:
            self.error(url, "Unknown content type: %s" % (content_type))
            return


    def update_stats(self, url, duration, content_size):
        stats = self.crawler.stats.setdefault(url.neutral_url(), {
            "first_duration"     : duration,
            "first_content_size" : content_size,
        })

        avg_duration     = (duration + stats.get("avg_duration", duration)) / 2.0
        avg_content_size = (content_size + stats.get("avg_content_size", content_size)) / 2.0

        stats.update({
            "orig_url"          : url.orig_url,
            "referer_url"       : url.referer_url,
            "num_visited"       : stats.get("num_visited", 0) + 1,
            "last_duration"     : duration,
            "last_content_size" : content_size,
            "avg_duration"      : avg_duration,
            "avg_content_size"  : avg_content_size,
        })


    def error(self, url, s):
        s = "[%s - found on %s] %s" % (url.url, url.referer_url, s)
        self.crawler.error(s)


    def check_response(self, url, response):
        soup = BeautifulSoup(response.text, "lxml")

        self.check_content(url, response, soup)
        self.check_images(url, soup)
        self.check_styles(url, soup)
        self.check_scripts(url, soup)
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


    def check_images(self, url, soup):
        self.check_referenced(url, soup, "img", "src")


    def check_referenced(self, referer_url, soup, tag, attr):
        elements = soup.find_all(tag)

        for element in elements:
            orig_url = element.get(attr)
            url = self.normalize_url(self.crawler.site.internal_url, orig_url)

            if url is not None and self.is_valid_url(url) \
               and url not in self.crawler.visited:
                #file("/tmp/todo", "a").write("%s (%s)\n" % (url, referer_url.url))
                self.crawler.todo.put(Url(url, orig_url=orig_url, referer_url=referer_url.url))


    def check_styles(self, url, soup):
        pass # TODO


    def check_scripts(self, url, soup):
        pass # TODO


    def is_valid_url(self, url):
        parsed = urlsplit(url)

        if parsed.scheme != "http":
            #print("invalid scheme: %r" % (parsed,))
            return False

        # skip external urls
        if url.startswith("http://") and not url.startswith(self.crawler.site.internal_url):
            #print("Skipping external URL: %s" % url)
            return False

        # skip non check_mk urls
        if not parsed.path.startswith("/%s/check_mk" % self.crawler.site.id) \
           or "../pnp4nagios/" in parsed.path \
           or "../nagvis/" in parsed.path \
           or "../nagios/" in parsed.path:
            #print("Skipping non Check_MK URL: %s %s" % (url, parsed))
            return False

	# skip current url with link to index
        if "index.py?start_url=" in url:
            #print("Skipping link to index with current URL: %s" % url)
            return False

        if "_transid=" in url:
            #print("Skipping action URL: %s" % url)
            return False

        if "selection=" in url:
            #print("Skipping selection URL: %s" % url)
            return False

        # Don't follow filled in filter form views
        if "view.py" in url and "filled_in=filter" in url:
            #print("Skipping filled in filter URL: %s" % url)
            return False

        # Skip agent download files
        if parsed.path.startswith("/%s/check_mk/agents/" % self.crawler.site.id):
            #print("Skipping agent download file: %s" % url)
            return False

        #print url
        return True # TODO


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
    @pytest.mark.env("ci-server")
    def test_crawl(self, site, web):
        self.stats   = {}
        self.todo    = SetQueue()
        self.started = time.time()
        self.visited = []
        self.errors  = []
        self.site    = site
        self.client  = web
        self.num_workers = 10

        self.load_stats()

        self.todo.put(Url(site.internal_url))

        self.crawl()

        self.report()


    def stats_file(self):
        return var_dir() + "/crawl.stats"


    def load_stats(self):
        try:
            self.stats = eval(file(self.stats_file()).read())
        except IOError, e:
            if e.errno == 2:
                pass # Not existing files are OK
            else:
                raise


    def save_stats(self):
        if not os.path.exists(var_dir()):
            os.makedirs(var_dir())
        file(self.stats_file()+".tmp", "w").write(pprint.pformat(self.stats) + "\n")
        os.rename(self.stats_file()+".tmp", self.stats_file())


    def update_total_stats(self, finished):
        stats = self.stats.setdefault("_TOTAL_", {})

        stats["last_num_visited"] = len(self.visited)
        stats["last_duration"]    = time.time() - self.started
        stats["last_errors"]      = self.errors
        stats["last_finished"]    = finished

        if finished:
            if stats.get("last_finished_num_visited", 0) > 0:
                perc = float(stats["last_num_visited"]) * 100 / stats["last_finished_num_visited"]
                if perc < 80.0:
                    self.error("Finished and walked %d URLs, previous run walked %d URLs. That "
                               "is %0.2f %% of the previous run. Something seems to be wrong."
                                 % (stats["last_num_visited"], stats["last_finished_num_visited"],
                                    perc))

            stats["last_finished_num_visited"] = stats["last_num_visited"]
            stats["last_finished_duration"]    = stats["last_duration"]
            stats["last_finished_errors"]      = stats["last_errors"]


    def report(self):
        if self.errors:
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
            while True:
                duration = max(time.time() - start, 1)
                num_visited = len(self.visited)
                num_idle = len([ w for w in workers if w.idle ])
                print("Workers: %d (Idle: %d), Rate: %0.2f/s, Duration: %d sec, "
                      "Visited: %s, Todo: %d" %
                    (self.num_workers, num_idle, num_visited / duration,
                     duration, num_visited, self.todo.qsize()))

                if self.todo.qsize() == 0 and all([ w.idle for w in workers ]):
                    break
                else:
                    time.sleep(1)

            finished = True
        except KeyboardInterrupt:
            for t in workers:
                t.stop()
            print "Waiting for workers to finish..."
        finally:
            self.update_total_stats(finished)
            self.save_stats()
