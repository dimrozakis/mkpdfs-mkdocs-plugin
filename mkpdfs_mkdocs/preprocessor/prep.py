import os

from .links import transform_href, transform_id, get_body_id, replace_asset_hrefs, rel_pdf_href

from weasyprint import urls
from bs4 import BeautifulSoup

def get_combined(soup: BeautifulSoup, base_url: str, rel_url: str):
    for id in soup.find_all(id=True):
        id['id'] = transform_id(id['id'], rel_url)

    for a in soup.find_all('a', href=True):
        if urls.url_is_absolute(a['href']) or os.path.isabs(a['href']):
            a['class'] = 'external-link'
            continue

        a['href'] = transform_href(a['href'], rel_url)

    soup.attrs['id'] = get_body_id(rel_url)
    soup = replace_asset_hrefs(soup, base_url)
    return soup

def get_separate(soup: BeautifulSoup, base_url: str):
    # transforms all relative hrefs pointing to other html docs
    # into relative pdf hrefs
    for a in soup.find_all('a', href=True):
        a['href'] = rel_pdf_href(a['href'])

    soup = replace_asset_hrefs(soup, base_url)
    return soup

def remove_header_links(soup: BeautifulSoup):
    for a in soup.find_all('a', **{'class': 'headerlink'}):
        a.decompose()
    return soup

def increment_headings(soup: BeautifulSoup, inc: int):
    if not inc:
        return soup
    assert isinstance(inc, int) and inc > 0
    for i in range(6, 0, -1):
        for h in soup.find_all('h{}'.format(i)):
            if i + inc > 6:
                print(h)
                raise ValueError("Exceeded maximum heading level. Can't nest "
                                 "h{} {} levels.".format(i, inc))
            h.name = 'h{}'.format(i + inc)
    return soup
