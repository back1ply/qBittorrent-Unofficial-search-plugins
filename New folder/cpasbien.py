# -*- coding: utf-8 -*-
# VERSION: 2.1
# AUTHOR: Davy39 <davy39@hmamail.com>, Paolo M
# CONTRIBUTORS: Simon <simon@brulhart.me>

# Copyleft


from __future__ import print_function
import urllib
import re

from html.parser import HTMLParser

from helpers import retrieve_url, headers, download_file
from novaprinter import prettyPrinter
import json


class cpasbien(object):
    # This is a fake url only for engine associations in file download
    url = "http://www.cpasbien.fr"
    name = "Cpasbien (french)"
    results_per_page = 50
    supported_categories = {
        "all": [""]
    }

    def __init__(self):
        self.real_url = self.find_url()

    def find_url(self):
        """Retrieve url from github repository, so it can work even if the url change"""
        link_github = "https://raw.githubusercontent.com/MarcBresson/cpasbien/master/urls.json"
        try:
            req = urllib.request.Request(link_github, headers=headers)
            response = urllib.request.urlopen(req)
            content = response.read().decode()
            urls = json.loads(content)
            return urls['cpasbien'][0]

        except urllib.error.URLError as errno:
            print(" ".join(("Connection error:", str(errno.reason))))
            return "http://www.cpasbien.moe"

    def download_torrent(self, desc_link):
        """find the link to the torrent"""
        req = urllib.request.Request(desc_link, headers=headers)

        try:
            response = urllib.request.urlopen(req)
        except urllib.error.URLError as errno:
            print(" ".join(("Connection error:", str(errno.reason))))
            return ""

        content = response.read().decode()

        link = self.real_url + re.findall('<a href="(\/get_torrent\/.*?)">', content)[0]

        print(download_file(link))

    def search(self, what, cat=None):
        results = []
        len_old_result = 0
        for page in range(10):
            url = f"{self.real_url}/recherche/{what}/{page * self.results_per_page + 1}"

            parser = TableRowExtractor(self.real_url, results)

            try:
                data = retrieve_url(url)
            except urllib.error.URLError as errno:
                print(" ".join(("Connection error:", str(errno.reason))))
                break

            parser.feed(data)
            results = parser.results
            parser.close()

            if len(results) - len_old_result == 0:
                break

            len_old_result = len(results)

        # Sort results
        good_order = [ord_res for _, ord_res in
                      sorted(zip([[int(res['seeds']), int(res['leech'])] for res in results], range(len(results))))]
        results = [results[x] for x in good_order[::-1]]

        # Fix size and add engine
        for i, res in enumerate(results):
            results[i]['size'] = unit_fr2en(res['size'])
            results[i]["engine_url"] = self.url
        # Print
        for res in results:
            prettyPrinter(res)


class TableRowExtractor(HTMLParser):
    def __init__(self, url, results):
        self.results = results
        self.map_name = {'titre': 'name', 'poid': 'size', 'up': 'seeds', 'down': 'leech'}
        self.in_tr = False
        self.in_table_corps = False
        self.in_div_or_anchor = False
        self.current_row = {}
        self.url = url
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            # check if the table has a class of "table-corps"
            attrs = dict(attrs)
            if attrs.get('class') == 'table-corps':
                self.in_table_corps = True

        if self.in_table_corps and tag == 'tr':
            self.in_tr = True

        if self.in_tr and tag in ['div', 'a']:
            # extract the class name of the div element if it exists
            self.in_div_or_anchor = True
            attrs = dict(attrs)
            self.current_div_class = self.map_name.get(attrs.get('class', None), None)
            if tag == 'a' and self.current_div_class == 'name':
                self.current_row['link'] = self.url + attrs['href']
                self.current_row["desc_link"] = self.url + attrs['href']

    def handle_endtag(self, tag):
        if tag == 'tr':
            if self.in_table_corps and 'desc_link' in self.current_row and self.current_row['desc_link'] not in [res['desc_link'] for res in self.results]:
                self.results.append(self.current_row)
            self.in_tr = False

            self.current_row = {}
        if tag == 'table':
            self.in_table_corps = False
        if tag in ['div', 'a']:
            self.in_div_or_anchor = False

    def handle_data(self, data):
        if self.in_div_or_anchor and self.current_div_class:
            self.current_row[self.current_div_class] = data

    def get_rows(self):
        return self.results


def unit_fr2en(size):
    """Convert french size unit to english"""
    return re.sub(
        r'([KMGTP])o',
        lambda match: match.group(1) + 'B',
        size, flags=re.IGNORECASE
    )
