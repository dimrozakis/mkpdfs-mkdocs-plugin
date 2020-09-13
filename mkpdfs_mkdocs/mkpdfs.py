import os
import sys
from timeit import default_timer as timer

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.commands.build import build

from weasyprint import HTML,urls, CSS
from bs4 import BeautifulSoup
from weasyprint.fonts import FontConfiguration

from mkpdfs_mkdocs.generator import Generator
from mkpdfs_mkdocs.utils import modify_html, modify_html_material

class Mkpdfs(BasePlugin):

    config_scheme = (
        ('design', config_options.Type(str, default=None)),
        ('design_extra', config_options.Type(str, default=None)),
        ('toc_title', config_options.Type(str, default="Table of Contents")),
        ('company', config_options.Type(str, default=None)),
        ('author', config_options.Type(str, default=None)),
        ('toc_position', config_options.Type(str, default="pre")),
        ('output_path', config_options.Type(str, default="pdf/combined.pdf")),
    )

    def __init__(self):
        self.generator = Generator()
        self.theme = ''

    def on_serve (self, server, config, **kwargs):
        # TODO: Implement watcher when the user is performing design
    #     print(server.watcher.__dict__)
    #     # builder = build(config, True, False)
    #     # server.watch(os.path.dirname(self.design), builder)
        return server

    def on_config(self, config, **kwargs):
        self.config['output_path'] = os.path.join("pdf", "combined.pdf") if not self.config['output_path'] else self.config['output_path']
        self.generator.set_config(self.config, config)
        self.theme = config['theme'].name
        return config

    def on_nav(self, nav, config, **kwargs):
        self.generator.add_nav(nav)
        return nav

    def on_post_page(self, output_content, page, config, **kwargs):
        try:
            abs_dest_path = page.file.abs_dest_path
            src_path = page.file.src_path
        except AttributeError:
            abs_dest_path = page.abs_output_path
            src_path = page.input_path
        path = os.path.dirname(abs_dest_path)
        os.makedirs(path, exist_ok=True)
        filename = os.path.splitext(os.path.basename(src_path))[0]
        base_url = urls.path2url(os.path.join(path, filename))
        pdf_url = self.generator.add_article(output_content, page, base_url)
        if pdf_url:
            if self.theme == 'material':
                output_content = modify_html_material(output_content, pdf_url)
            else:
                output_content = modify_html(output_content, pdf_url)
        return output_content

    def on_post_build(self, config):
        self.generator.write()
