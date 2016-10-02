from __future__ import unicode_literals
import urllib
import urllib2
from bs4 import BeautifulSoup as BS
import re
from urlparse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import json


class Remote(object):
    def __init__(self, url=None):
        if url:
            if url.startswith('//'):
                url = 'http:' + url
            elif url.startswith('/'):
                url = 'http://fs.to' + url
            self.movie_id = re.match(r'.*/([a-zA-Z0-9]+)\-.*\.html.*', url).groups()[0]
        else:
            self.movie_id = None
        self.url = url

    def _request(self, url, **kwargs):
        response = urllib2.urlopen(url + '?' + urllib.urlencode(kwargs))
        return response.read()

    def _json_request(self, url, **kwargs):
        return json.loads(self._request(url, **kwargs))

    def _html_request(self, url, **kwargs):
        return BS(self._request(url, **kwargs), 'html.parser')


class FSApi(Remote):
    def __init__(self):
        super(FSApi, self).__init__(None)

    def search(self, query):
        return [
            FSMovie(item['link'], item['title'], item['poster'])
            for item
            in self._json_request(
                'http://fs.to/search.aspx',
                f='quick_search', search=query, limit=10, mod='main'
            )
        ]


class FSMovie(Remote):
    def __init__(self, url, title, poster):
        super(FSMovie, self).__init__(url)

        self.title = title
        self.poster = poster

    def get_root_folder(self):
        return FSFolder(self.url, 'Root folder', 0)


class FSNode(object):
    def __repr__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u' / '.join(filter(None, (
            unicode(self.parent) if self.parent else None,
            # u'[{}] {}'.format(getattr(self, 'folder_id', getattr(self, 'file_id', None)), self.title)
            self.title
        )))

    def dump(self, depth=0):
        # print 'DIR ' if isinstance(self, FSFolder) else 'FILE', unicode(self)
        print unicode(self)
        if isinstance(self, FSFolder):
            for item in self.items:
                # print (u'    ' * depth * 4) + unicode(self)
                # if isinstance(item, FSFolder):
                item.dump(depth + 1)

    def get_tree(self):
        if isinstance(self, FSFolder):
            return {
                item.title: item.get_tree()
                for item
                in self.items
            }
        return self

    @property
    def type(self):
        return self.__class__._type


class FSFolder(Remote, FSNode):
    type = 'folder'

    def __init__(self, url, title, folder_id, parent=None, cached_data=None):
        super(FSFolder, self).__init__(url)

        self._title = title
        self.folder_id = folder_id
        self.parent = parent

        self._items = None

    @property
    def title(self):
        return self._title

    @property
    def items(self):
        if not self._items:
            self._items = list(self._refresh())
        return self._items

    def _refresh(self):
        doc = self._html_request(self.url, ajax=1, id=self.movie_id, folder=self.folder_id)
        for item in doc.select('> ul > li'):
            # print doc
            # print etree.dump(item)
            # if 'name' not in item.select_one('a'):
            #     print '!!!'
            #     print item, item.select_one('a')
            #     print '...'
            title = None

            if not title:
                name_el = item.select_one('> .header > a > b')
                if name_el:
                    title = name_el.text
            if not title:
                name_el = item.select_one('> a > span > .b-file-new__link-material-filename-text')
                if name_el:
                    title = name_el.text
            if not title:
                name_el = item.select_one('> div > a')
                if name_el:
                    title = name_el.text

            a = item.select_one('a')
            if a['href'].startswith('/') and 'name' not in a:
                url_info = urlparse(a['href'])
                query = parse_qs(url_info.query)
                id, quality = query.get('file')[0], query.get('quality', [None])[0]
                # params = dict(map(lambda pair: pair.split('='), a['href'].split(';')[1:]))
                # print a['href'], a['href'].split(';')[1:]
                yield FSFile(self.url, title, id, self, quality)
            else:
                yield FSFolder(self.url, title, a['name'][2:], self)


class FSFile(Remote, FSNode):
    type = 'file'

    def __init__(self, url, title, file_id, parent=None, quality=None):
        super(FSFile, self).__init__(url)

        self._title = title
        self.file_id = file_id
        self.parent = parent
        self.quality = quality

    # def __repr__(self):
    #     return unicode(self).encode('utf-8')

    @property
    def title(self):
        # print u' [{}]'.format(self.quality if self.quality else u'default')
        return u'[{}] {} - {}'.format(
            self.file_id,
            self._title,
            self.quality if self.quality else u'default'
        )

    def get_file_url(self):
        driver = webdriver.Chrome()
        print 'get...'
        driver.get('http://fs.to/video/cartoonserials/view_iframe/{}?play&file={}'.format(self.movie_id, self.file_id))
        print 'get done!'

        print 'w1...'
        WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.XPATH, "//video"))
        )
        print 'w1 done!'

        driver.execute_script('''
            console.log('START');
            var overlay = document.createElement('div');
            overlay.innerHTML = 'Please wait...';
            overlay.style.background = 'rgba(0, 0, 0, 0.7)';
            overlay.style.position = 'absolute';
            overlay.style.lineHeight = '100vh';
            overlay.style.fontSize = '10vh';
            overlay.style.textAlign = 'center';
            overlay.style.color = '#FFF';
            ['left', 'top', 'bottom', 'right'].forEach(function(attr) {
                overlay.style[attr] = '0';
            });
            overlay.style.zIndex = 13371337;
            document.body.appendChild(overlay);
            console.log(overlay);
            [].forEach.call(document.querySelectorAll('video'), function(video) {
                video.pause();
            });
        ''')

        print 'w2...'

        WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.ID, "player"))
        )

        print 'w2 done!'

        # driver.save_screenshot('1.png')
        # print element.get_attribute('src')
        # driver.execute_script('window.location = document.querySelector("#player.m-hidden").src;')
        url = driver.execute_script('return document.querySelector("#player.m-hidden").src;')
        subprocess.Popen(['vlc', url])
        driver.close()
        # print element
        # print driver.execute_script('return document.getElementById("player");')
