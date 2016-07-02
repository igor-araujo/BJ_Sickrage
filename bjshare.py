# coding=utf-8
# Author: Niteck <niteckbj@gmail.com>
#
# This file was developed as a 3rd party provider for SickRage.
# It is not part of SickRage's oficial repository.
#
# SickRage is free software: distributed under the terms of the
# GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import requests

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider

class BJShareProvider(TorrentProvider):
    
    def __init__(self):
        
        # Provider Init
        TorrentProvider.__init__(self, "BJ-Share")
        
        # Credentials
        self.api_key = None
    
        # Torrent Stats
        self.minseed = None
        self.minleech = None
        
        self.urls = {"base_url" : "https://www.bj-share.me/",
                     "login" : "https://www.bj-share.me/login.php",
                     "search" : "https://bj-share.me/torrents.php"}
        
        self.url = self.urls['base_url']
        
        self.cache = tvcache.TVCache(self, min_time=15)  # only poll  BJ-Share every 15 minutes max
    
    def login(self):
        self._session = requests.session()
        self._session.cookies.set('session', self.api_key)
        
        try:
            response = self._session.get(self.urls["login"])
        except requests.exceptions.TooManyRedirects:
            logger.log(u"Unable to connect to provider. Check your SESSION cookie", logger.WARNING)
            return False
        
        if not response.ok:
            logger.log(u"Unable to connect to provider", logger.WARNING)
            return False
        
        with BS4Parser(response.text, "html5lib") as html:
            if html.title.text.split()[0] == u"Login":
                logger.log(u"Invalid SESSION cookie. Check your settings", logger.WARNING)
                return False
        
        return True
    
        
    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals
        results = []
        
        if not self.login():
            return results
        
        params = {"searchstr" : "",
                  "order_way" : "desc",
                  "order_by" :"seeders",
                  "filter_cat[2]" : "1"}
        
        def has_attrs_files_(tag):
            try:
                return tag.has_attr("id") and "files_" in tag["id"]
            except KeyError:
                return False
        
        for mode in search_params:
            items = []
            logger.log("Search mode: {0}".format(mode), logger.DEBUG)
            
            if mode == "RSS":
                logger.log("RSS search is not implemented yet", logger.DEBUG)
                continue
            
            search_url = self.urls["search"]
            
            for search_string in search_params[mode]:
                
                search_string = re.sub("\(.+\)", "", search_string)
                params["searchstr"] = '+'.join([x for x in search_string.split()[:-1]])
                episode = search_string.split()[-1]
                logger.log("Search string: {}".format(search_string.decode("utf-8")), logger.DEBUG)

                search_url += "?"+"&".join(["{0}={1}".format(key,value) for key,value in params.items()])

                data = self._session.get(search_url)

                with BS4Parser(data.text, "html5lib") as html:
                    try:
                        torrent_group = html.find("div",
                                                  class_='group_info').find("a",title="View torrent group").attrs["href"]
                    except AttributeError:
                        logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue

                data = self._session.get("{0}{1}".format(self.urls["base_url"], torrent_group))
                
                if not data:
                    logger.log("URL did not return data, maybe try a custom url, or a different one", logger.DEBUG)
                    continue
                
                with BS4Parser(data.text, "html5lib") as html:
                    torrent_table = html.find_all("tr", class_="group_torrent")
                    
                    if not torrent_table:
                        logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue
                    
                    for result in torrent_table:
                        if result.find("a", href="#").text.split()[0] != episode:
                            continue

                        title = result.find_next_sibling().find("div", class_="filelist_path").text.replace("/","")
                        download_file = "{0}{1}".format(self.urls["base_url"],
                                                        result.find("a", title="Baixar").attrs["href"])

                        if not all([title, download_file]):
                            continue

                        torrent_size, snatches, seeders, leechers = result.find_all("td", class_="number_column")
                        torrent_size, snatches, seeders, leechers = torrent_size.text, snatches.text, seeders.text, leechers.text

                        # Filter unseeded torrent
                        if seeders < self.minseed or leechers < self.minleech:
                            logger.log("Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                           (title, seeders, leechers), logger.DEBUG)
                            continue

                        size = convert_size(torrent_size) or -1

                        item = {'title': title,
                                'link': download_file,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'hash': ''}

                        logger.log("Found result: {0} with {1} seeders and {2} leechers".format
                                   (title,seeders, leechers), logger.DEBUG)

                        items.append(item)
                        
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items
        
        return results
    
provider = BJShareProvider()
