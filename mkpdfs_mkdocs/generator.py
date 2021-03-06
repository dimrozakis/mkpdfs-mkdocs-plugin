import logging
import os
import sys
from uuid import uuid4
from timeit import default_timer as timer

from weasyprint import HTML,urls, CSS
from bs4 import BeautifulSoup
from weasyprint.fonts import FontConfiguration

from mkpdfs_mkdocs.utils import gen_address
from mkpdfs_mkdocs.preprocessor import get_separate as prep_separate, get_combined as prep_combined
from mkpdfs_mkdocs.preprocessor import increment_headings, remove_header_links
from mkpdfs_mkdocs.preprocessor import remove_material_header_icons

log = logging.getLogger(__name__)

class Generator(object):

    def __init__(self):
        self.config = None
        self.design = None
        self.mkdconfig = None
        self.nav = None
        self.logger = logging.getLogger('mkdocs.mkpdfs')
        self.generate = True
        self._articles = {}
        self._page_order = []
        self._page_nesting = {}
        self._base_urls = {}
        self._toc = None
        self.html = BeautifulSoup('<html><head></head>\
        <body></body></html>',
        'html.parser')
        self.dir = os.path.dirname(os.path.realpath(__file__))
        self.design = os.path.join(self.dir, 'design/report.css')
        self.design_extra = ''

    def set_config(self, local, config):
        self.config = local;
        for key in ('design', 'design_extra'):
            if self.config[key]:
                css_file = os.path.join(os.getcwd(), self.config[key])
                if not os.path.isfile(css_file) :
                    sys.exit('The file {} specified for {} has not \
                    been found.'.format(css_file, key))
                setattr(self, key, css_file)
        self.title = config['site_name']
        self.config['copyright'] = 'CC-BY-SA\
        ' if not config['copyright'] else config['copyright']
        self.mkdconfig = config

    def write(self):
        if not self.generate:
            self.logger.log(msg='Unable to generate the PDF Version (See Mkpdfs doc)',
            level=logging.WARNING,)
            return
        self.gen_articles()
        font_config = FontConfiguration()
        self.add_head()
        pdf_path = os.path.join(self.mkdconfig['site_dir'],
        self.config['output_path'])
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        html = HTML(string=str(self.html)).write_pdf(pdf_path,
        font_config=font_config)
        self.logger.log(msg='The PDF version of the documentation has been generated.', level=logging.INFO,)

    def add_nav(self, nav):
        self.nav = nav
        for p in nav:
            self.addToOrder(p)

    def addToOrder(self, page, level=1):
        if page.is_page and page.meta != None and 'pdf' in page.meta and page.meta['pdf'] == False:
            print(page.meta)
            exit(1)
            return;
        if page.is_page :
            self._page_nesting[page.file.url] = level - 1
            self._page_order.append(page.file.url)
        else :
            uuid = str(uuid4())
            self._page_order.append(uuid)
            title = self.html.new_tag('h{}'.format(level),
                id='{}-title'.format(uuid),
                **{'class': 'section_title'}
            )
            title.append(page.title)
            article = self.html.new_tag('article',
                id='{}'.format(uuid),
                **{'class': 'chapter'}
            )
            article.append(title)
            self._articles[uuid] = article
            for child in page.children:
                self.addToOrder(child, level=level+1)


    def remove_from_order(self, item):

        return

    def add_article(self, content, page, base_url):
        if not self.generate:
            return None
        self._base_urls[page.file.url] = base_url
        soup = BeautifulSoup(content, 'html.parser')
        url = page.url[:-5] if page.url.endswith('.html') else page.url
        article = soup.find('article')
        if not article :
            article = self.html.new_tag('article')
            eld = soup.find('div', **{'role': 'main'})
            article.append(eld)
            article.div['class'] = article.div['role'] = None

        if not article:
            self.generate = False
            return None
        article = increment_headings(
            remove_header_links(
                prep_combined(
                    remove_material_header_icons(article),
                    base_url, page.file.url,
                ),
            ),
            self._page_nesting.get(page.file.url, 0),
        )
        span = soup.new_tag('span')
        span['id'] = 'mkpdf-{}'.format(url)
        article.insert(0, span)
        if page.meta != None and 'pdf' in page.meta and page.meta['pdf'] == False:
            # print(page.meta)
            return self.get_path_to_pdf(page.file.dest_path)
        self._articles[page.file.url] = article
        return self.get_path_to_pdf(page.file.dest_path)

    def add_head(self):
        lines = ['<title>{}</title>'.format(self.title)]
        for key, val in (
            ("author", self.config['author'] or self.mkdconfig['site_author']),
            ("description", self.mkdconfig['site_description']),
        ):
            if val:
                lines.append('<meta name="{}" content="{}">'.format(key, val))
        for css in (self.design, self.design_extra):
            if css:
                css_tmpl = '<link rel="stylesheet" href="{}" type="text/css">'
                lines.append(css_tmpl.format(urls.path2url(css)))
        head = BeautifulSoup('\n'.join(lines), 'html5lib')
        self.html.head.clear()
        self.html.head.insert(0, head)

    def add_tocs(self):
        title = self.html.new_tag('h1', id='toc-title')
        title.insert(0, self.config['toc_title'])
        self._toc = self.html.new_tag('article', id='contents')
        self._toc.insert(0, title)
        for n in self.nav:
            if n.is_page and n.meta != None and 'pdf' in n.meta \
            and n.meta['pdf'] == False:
                continue
            h3 = self.html.new_tag('h3')
            h3.insert(0, n.title)
            self._toc.append(h3)
            if n.is_page :
                ptoc = self._gen_toc_page(n.file.url, n.toc)
                self._toc.append(ptoc)
            else :
                self._gen_toc_section(n)
        self.html.body.append(self._toc)

    def add_cover(self):
        a = self.html.new_tag('article', id='doc-cover')
        title = self.html.new_tag('h1', id='doc-title')
        title.insert(0, self.title)
        a.insert(0, title)
        a.append(gen_address(self.config))
        self.html.body.append(a)

    def gen_articles (self):
        self.add_cover()
        if self.config['toc_position'] == 'pre' :
            self.add_tocs()
        for url in self._page_order:
            if url in self._articles:
                self.html.body.append(self._articles[url])
        if self.config['toc_position'] == 'post' :
            self.add_tocs()

    def get_path_to_pdf(self, start):
        return os.path.relpath(self.config['output_path'],
                               os.path.dirname(start))

    def _gen_toc_section(self, section):
        for p in section.children:
            if p.is_page and p.meta != None and 'pdf' \
            in p.meta and p.meta['pdf'] == False:
                continue
            if p.is_section:
                h3 = self.html.new_tag('h3')
                h3.insert(0, p.title)
                self._toc.append(h3)
                self._gen_toc_section(p)
                continue
            stoc = self._gen_toc_for_section(p.file.url, p)
            child = self.html.new_tag('div')
            child.append(stoc)
            self._toc.append(child)

    def _gen_children(self, url, children):
        ul = self.html.new_tag('ul')
        for child in children:
            a = self.html.new_tag('a', href=child.url)
            a.insert(0, child.title)
            li = self.html.new_tag('li')
            li.append(a)
            if child.children :
                sub = self._gen_children(url, child.children)
                li.append(sub)
            ul.append(li)
        return ul
    def _gen_toc_for_section(self, url, p):
        div = self.html.new_tag('div')
        menu = self.html.new_tag('div')
        h4 = self.html.new_tag('h4')
        urlid = url[:-5] if url.endswith('.html') else url
        a = self.html.new_tag('a', href='#mkpdf-{}'.format(urlid))
        a.insert(0, p.title)
        h4.append(a)
        menu.append(h4)
        ul = self.html.new_tag('ul')
        for child in p.toc.items:
            a = self.html.new_tag('a', href=child.url)
            a.insert(0, child.title)
            li = self.html.new_tag('li')
            li.append(a)
            if child.title == p.title:
                li = self.html.new_tag('div');
            if child.children :
                sub = self._gen_children(url, child.children)
                li.append(sub)
            ul.append(li)
        if len(p.toc.items)>0:
            menu.append(ul)
        div.append(menu)
        div = prep_combined(div, self._base_urls[url], url)
        return div.find('div')

    def _gen_toc_page(self, url, toc):
        div = self.html.new_tag('div')
        menu = self.html.new_tag('ul')
        for item in toc.items:
            li = self.html.new_tag('li')
            a = self.html.new_tag('a', href=item.url)
            a.append(item.title)
            li.append(a)
            menu.append(li)
            if item.children :
                child = self._gen_children(url, item.children)
                menu.append(child)
        div.append(menu)
        div = prep_combined(div, self._base_urls[url], url)
        return div.find('ul')
