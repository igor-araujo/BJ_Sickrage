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
import sickrage
from sickrage.core.caches.tv_cache import TVCache
from sickrage.core.helpers import try_int, convert_size, bs4_parser
from sickrage.providers import TorrentProvider

class BJShareProvider(TorrentProvider):
    
    def __init__(self):
        
        # Provider Init
        super(BJShareProvider, self).__init__('BJ-Share',"https://bj-share.info", True)
        
        # Credentials
        self.username = None
        self.password = None
    
        # Torrent Stats
        self.minseed = None
        self.minleech = None
        
        self.urls.update = {
                     'login': '{base_url}/login.php'.format(**self.urls),
                     'search': '{base_url}/torrents.php'.format(**self.urls)}
        
        self.url = self.urls['base_url']
        
        self.cache = TVCache(self, min_time=15)  # only poll BJ-Share every 15 minutes max
  
    
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
        
        if not self.session.post(self.urls['login'], data=login_params).text:
            sickrage.app.log.warning(u"Unable to connect to provider")
            return False
        
        response = self.session.get("https://bj-share.info/index.php").text
        
        if re.search('<title>Login :: BJ-Share</title>', response):
            sickrage.app.log.warning(u"Invalid username or password. Check your settings")
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
                sickrage.app.log.warning(u"Found an invalid show resolution: {}. Using default value (SD).".format(show_info['Resolution']))
                show_info['Resolution'] = ''

            name = ' '.join(x for x in [show_info['Name'],extra,show_info['SE'],show_info['Resolution'],
                                        show_info['Quality'],show_info['Video'],show_info['Extension'].lower()])
            name = re.sub('[\.\ ]+', '.', name)

            return name


        for mode in search_params:
            items = []
            sickrage.app.log.debug(u"Search mode: {0}".format(mode))
            
            if mode == 'RSS':
                sickrage.app.log.debug(u"RSS search is not implemented yet")
                continue
            
            for search_string in search_params[mode]:
                original_str = search_string
                try:
                    extra_string = re.search('\(.+\)',search_string).group()
                except AttributeError:
                    extra_string = ''
                
                search_string = re.sub('\ +\(.+\)', '', search_string)
                params['searchstr'], episode = search_string.rsplit(' ',1)
                sickrage.app.log.debug(u"Search string: {}".format(original_str.decode('utf-8')))
                
                search_url = self.urls['search'] + '?' + urlencode(params)
                data = self.session.get(search_url).text

                with bs4_parser(data) as html:
                    try:
                        torrent_group = html.find('div',
                                                  class_='group_info').find('a',title="View torrent group").attrs['href']
                    except AttributeError:
                        sickrage.app.log.debug(u"Data returned from provider does not contain any torrents")
                        continue

                data = self.session.get(urljoin(self.urls['base_url'], torrent_group)).text
                
                if not data:
                    sickrage.app.log.debug(u"URL did not return data, maybe try a custom url, or a different one")
                    continue
                
                with bs4_parser(data) as html:
                    torrent_table = html.find_all('tr', class_='group_torrent')
                    
                    if not torrent_table:
                        sickrage.app.log.debug(u"Data returned from provider does not contain any torrents")
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
                            sickrage.app.log.debug(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: "
                                       u"{0} (S:{1} L:{2})".format(title, seeders, leechers))
                            continue

                        size = convert_size(torrent_size) or -1

                        item = {'title': title,
                                'link': download_file,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'hash': ''}

                        sickrage.app.log.debug(u"Found result: {0} with {1} seeders and {2} "
                                   u"leechers".format(title, seeders, leechers))

                        items.append(item)
                        
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items
        
        return results
    
provider = BJShareProvider()
