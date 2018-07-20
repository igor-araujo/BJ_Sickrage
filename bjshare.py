# coding=utf-8
# Author: Gabriel Bertacco <niteckbj@gmail.com>
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

import re
import requests
from requests.compat import urljoin
try:
    from urllib import urlencode    # Python3 Import
except ImportError:
    from urllib.parse import urlencode    # Python2 Import
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider

class BJShareProvider(TorrentProvider):
    
    def __init__(self):
        
        # Provider Init
        TorrentProvider.__init__(self, 'BJ-Share')
        
        # Credentials
        self.username = None
        self.password = None
    
        # Torrent Stats
        self.minseed = None
        self.minleech = None
        
        self.urls = {'base_url': "https://bj-share.info/",
                     'login': "https://bj-share.info/login.php",
                     'search': "https://bj-share.info/torrents.php"}
        
        self.url = self.urls['base_url']
        
        self.cache = tvcache.TVCache(self, min_time=15)  # only poll BJ-Share every 15 minutes max
  
    
    def login(self):
        cookie_dict = requests.utils.dict_from_cookiejar(self.session.cookies)
        if cookie_dict.get('session'):
            return True
        
        login_params = {
            'submit': 'Login',
            'username': self.username,
            'password': self.password,
            'keeplogged': 0,
        }
        
        if not self.get_url(self.urls['login'], post_data=login_params, returns='text'):
            logger.log(u"Unable to connect to provider", logger.WARNING)
            return False
        
        response = self.get_url(urljoin(self.urls['base_url'],'index.php'), returns='text')
        
        if re.search('<title>Login :: BJ-Share</title>', response):
            logger.log(u"Invalid username or password. Check your settings", logger.WARNING)
            return False
        
        return True

        
    def search(self, search_params, age=0, ep_obj=None):
        results = []
        
        if not self.login():
            return results
        
        params = {'searchstr': '',
                  'order_way': 'desc',
                  'order_by':'seeders',
                  'filter_cat[2]': '1'}

        def get_show_name(html,**kwargs):
            if not html:
                return
            
            extra = kwargs.pop('extra', '')
            
            # Wanted show infos
            show_info = {
                'Extension': "Formato",
                'Quality': "Qualidade",
                'Audio': "Codec de \xc3\x81udio",
                'Video': "Codec de V\xc3\xaddeo",
                'Resolution': "Resolu\xc3\xa7\xc3\xa3o"
            }
            
            for key,value in show_info.items():
                show_info[key] = re.match('.+:\ (.*)',html.find_next('blockquote',text=re.compile('%s.*'%value)).text).groups()[0]

            show_info['Name'] = re.match('(.+)\ \[\d+\]',
                                         html.find_parent('div', class_='thin').find('div', class_='header').h2.text).group(1)
            
            if re.match('.+\[(.+)\]', show_info['Name']):
                show_info['Name'] = re.match('.+\[(.+)\]', show_info['Name']).group(1)
                                         
            show_info['SE'] = html.find('a', href='#').text.split()[0]
            
            show_info['Video'] = re.sub('H.','x',show_info['Video'])

            try:
                resolution = int(re.search('\d+',show_info['Resolution']).group(0))
    
                if 1260 <= resolution <= 1300:
                    show_info['Resolution'] = '720p'
                elif 1900 <= resolution <= 1940:
                    show_info['Resolution'] = '1080p'
                else:
                    show_info['Resolution'] = ''
            except ValueError:
                logger.log(u"Found an invalid show resolution: {}. Using default value (SD).".format(show_info['Resolution']),
                           logger.WARNING)
                show_info['Resolution'] = ''

            name = ' '.join(x for x in [show_info['Name'],extra,show_info['SE'],show_info['Resolution'],
                                        show_info['Quality'],show_info['Video'],show_info['Extension'].lower()])
            name = re.sub('[\.\ ]+', '.', name)

            return name


        for mode in search_params:
            items = []
            logger.log(u"Search mode: {0}".format(mode), logger.DEBUG)
            
            if mode == 'RSS':
                logger.log(u"RSS search is not implemented yet", logger.DEBUG)
                continue
            
            for search_string in search_params[mode]:
                original_str = search_string
                try:
                    extra_string = re.search('\(.+\)',search_string).group()
                except AttributeError:
                    extra_string = ''
                
                search_string = re.sub('\ +\(.+\)', '', search_string)
                params['searchstr'], episode = search_string.rsplit(' ',1)
                logger.log(u"Search string: {}".format(original_str.decode('utf-8')), logger.DEBUG)
                
                search_url = self.urls['search'] + '?' + urlencode(params)
                data = self.get_url(search_url, returns='text')

                with BS4Parser(data, 'html5lib') as html:
                    try:
                        torrent_group = html.find('div',
                                                  class_='group_info').find('a',title="View torrent group").attrs['href']
                    except AttributeError:
                        logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue

                data = self.get_url(urljoin(self.urls['base_url'], torrent_group), returns='text')
                
                if not data:
                    logger.log(u"URL did not return data, maybe try a custom url, or a different one", logger.DEBUG)
                    continue
                
                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find_all('tr', class_='group_torrent')
                    
                    if not torrent_table:
                        logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue
                    
                    for result in torrent_table:
                        if result.find('a', href='#').text.split()[0] != episode:
                            continue

                        title = get_show_name(result,extra=extra_string)
                        download_file = urljoin(self.urls['base_url'],
                                                result.find('a', title='Baixar').attrs['href'])

                        if not all([title, download_file]):
                            continue

                        torrent_size, snatches, seeders, leechers = [x.text for x in result.find_all('td', class_='number_column')]

                        # Filter unseeded torrent
                        if seeders < self.minseed or leechers < self.minleech:
                            logger.log(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: "
                                       u"{0} (S:{1} L:{2})".format(title, seeders, leechers), logger.DEBUG)
                            continue

                        size = convert_size(torrent_size) or -1

                        item = {'title': title,
                                'link': download_file,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'hash': ''}

                        logger.log(u"Found result: {0} with {1} seeders and {2} "
                                   u"leechers".format(title, seeders, leechers), logger.DEBUG)

                        items.append(item)
                        
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items
        
        return results
    
provider = BJShareProvider()
