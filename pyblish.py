#!/usr/bin/python3

import argparse
from subprocess import Popen, PIPE, call
import yaml
from os.path import exists
from os import remove
from typing import List


class Extensions:
    def __init__(self):
        self._enabled = set()
        self._disabled = set()

    def default(self, extension):
        if extension in self._enabled:
            self._enabled.remove(extension)
        if extension in self._disabled:
            self._disabled.remove(extension)

    def enable(self, extension):
        if extension in self._disabled:
            self._disabled.remove(extension)
        self._enabled.add(extension)

    def disable(self, extension):
        if extension in self._enabled:
            self._enabled.remove(extension)
        self._disabled.add(extension)

    def __repr__(self):
        extensions = []
        for e in self._enabled:
            extensions.append('+')
            extensions.append(e)
        for d in self._disabled:
            extensions.append('-')
            extensions.append(d)
        return ''.join(extensions)


def read_metadata(path):
    data = {}
    with open(path, 'r') as metadata:
        yml = yaml.safe_load(metadata.read())
        if yml is not None:
            data = yml
        if 'use' in data:
            use_path = data['use']
            del data['use']
            data.update(read_metadata(use_path))
    return data


class _PyblishConverter:
    def __init__(self):
        self._extensions = {}
        self._filters = []
        self._options = {}

    def enable_extension(self, format, extension):
        if format not in self._extensions:
            self._extensions[format] = Extensions()
        self._extensions[format].enable(extension)

    def disable_extension(self, format, extension):
        if format not in self._extensions:
            self._extensions[format] = Extensions()
        self._extensions[format].disable(extension)

    def default_extension(self, format, extension):
        if format not in self._extensions:
            self._extensions[format] = Extensions()
        self._extensions[format].default(extension)

    def add_filter(self, filter):
        self._filters.append(filter)

    def remove_filter(self, filter):
        if filter in self._filters:
            self._filters.remove(filter)

    def _build(self, input_format, output_format, standalone):
        cmd = [
            'pandoc',
            '-f', input_format + str(self._extensions.get(input_format, Extensions())),
            '-t', output_format
        ]

        for f in self._filters:
            cmd.append("--filter")
            cmd.append('_filters/' + f)

        if output_format in self._options:
            options = self._options[output_format]
            for key in options:
                if not standalone and key == 'template':
                    continue
                value = options[key]
                cmd.append('--' + key)
                if value != True:
                    cmd.append(value)
        if standalone:
            cmd.append('-s')
        return cmd

    def _debug(self, input_format, output_format, standalone):
        return ' '.join(self._build(input_format, output_format, standalone))

    def format(self, input, input_format, output_format):
        p = Popen(self._build(input_format, output_format, False), stdin=PIPE, stdout=PIPE)
        return p.communicate(input=input.encode())[0].decode()

    def format_from_files(self, inputs: List[str], output: str, input_format: str, output_format: str, *args):
        p = Popen(tuple(self._build(input_format, output_format, True)) + tuple(inputs) + args,
                  stdout=open(output, 'wb'))
        p.wait()

    def configure(self, path):
        conf = read_metadata(path)
        if 'filters' in conf:
            for filter in conf['filters']:
                self.add_filter(filter)
        self._extensions.clear()
        if 'from' in conf:
            extensions = conf['from']
            for fmt in extensions:
                fmt_extensions = extensions[fmt]
                if 'enable' in fmt_extensions:
                    for extension in fmt_extensions['enable']:
                        self.enable_extension(fmt, extension)
                if 'disable' in fmt_extensions:
                    for extension in fmt_extensions['disable']:
                        self.disable_extension(fmt, extension)
        self._options.clear()
        if 'to' in conf:
            self._options.update(conf['to'])
        if 'to' in conf:
            if 'ipynb' in conf['to']:
                if 'style' in conf['to']['ipynb']:
                    try:
                        from IPython.display import HTML
                        import IPython.display
                        with open(conf['to']['ipynb']['style']) as css:
                            style = css.read()
                            style = style.strip()
                            display(HTML('<style>' + style + '</style>'))
                    except ImportError:
                        pass


Pyblish = _PyblishConverter()

def safe_repr_html(obj):
    try:
        from IPython.display import Markdown
        if isinstance(obj, Markdown):
            return Pyblish.format(obj.data, 'markdown', 'html')
    except ImportError:
        pass
    try:
        repr = obj._repr_html_()
        if repr is not None:
            return repr
        return str(obj)
    except AttributeError:
        return str(obj)


def safe_repr_latex(obj):
    try:
        from IPython.display import Image
        if isinstance(obj, Image):
            return f"\\includegraphics{{{obj.url}}}"
    except ImportError:
        pass
    try:
        from IPython.display import Markdown
        if isinstance(obj, Markdown):
            return Pyblish.format(obj.data, 'markdown', 'latex')
    except ImportError:
        pass
    try:
        repr = obj._repr_latex_()
        if repr is not None:
            return repr
        repr = obj._repr_html_()
        if repr is not None:
            return Pyblish.format(repr, 'html', 'latex')
        return str(obj)
    except AttributeError:
        return str(obj)


class Tag:
    def __init__(self, children, html_tag, latex_tag, raw):
        self.html_tag = html_tag
        if latex_tag is None:
            self.latex_tag = html_tag
        else:
            self.latex_tag = latex_tag
        self.children = []
        for child in children:
            if not raw and isinstance(child, str):
                try:
                    from IPython.display import Markdown
                    self.children.append(Markdown(child))
                except ImportError:
                    self.children.append(child)
            else:
                self.children.append(child)

    def _repr_html_(self):
        children_repr = []
        if self.children is not None:
            for child in self.children:
                children_repr.append(safe_repr_html(child))
        if self.html_tag:
            return '<' + self.html_tag + '>' + ''.join(children_repr) + '</' + self.html_tag + '>'
        return ''.join(children_repr)


class BlockTag(Tag):
    def __init__(self, children, html_tag, latex_tag=None, raw=False):
        super().__init__(children, html_tag, latex_tag, raw)

    def _repr_latex_(self):
        children_repr = []
        if self.children is not None:
            for child in self.children:
                children_repr.append(safe_repr_latex(child))
        if self.latex_tag:
            return '\\begin{' + self.latex_tag + '}' + ''.join(children_repr) + '\\end{' + self.latex_tag + '}'
        return ''.join(children_repr)


class InlineTag(Tag):
    def __init__(self, children, html_tag, latex_tag=None, raw=False):
        super().__init__(children, html_tag, latex_tag, raw)

    def _repr_latex_(self):
        children_repr = []
        for child in self.children:
            children_repr.append(safe_repr_latex(child))
        if self.latex_tag:
            return '\\' + self.latex_tag + '{' + ''.join(children_repr) + '}'
        return ''.join(children_repr)


class Figure(BlockTag):
    def __init__(self, *children):
        super().__init__(children, 'figure')


class Table(BlockTag):
    def __init__(self, *children):
        super().__init__(children, 'div', 'table')


class Center(BlockTag):
    def __init__(self, *children):
        super().__init__(children, 'center')


class Tikz:
    def __init__(self, name, content, inlined=False):
        self._name = name
        self._content = content
        self._inlined = inlined
        pdf = name + '.pdf'
        tex = name + '.tex'
        svg = name + '.svg'

        content = f"""
\\documentclass[crop,tikz]{{standalone}}
\\begin{{document}}
\\begin{{tikzpicture}}
{content}
\\end{{tikzpicture}}
\\end{{document}}
""".strip()

        with open(tex, 'w') as standalone:
            standalone.write(content)
        from subprocess import call, DEVNULL
        call(['latexmk', '-pdf', tex], stdout=DEVNULL)
        from os.path import exists
        from os import remove
        for extension in ['aux', 'dvi', 'fdb_latexmk', 'fls', 'log', 'ps']:
            filename = f"{name}.{extension}"
            if exists(filename):
                remove(filename)
        call(['inkscape', pdf, '--export-filename', svg], stdout=DEVNULL)

    def _repr_html_(self):
        from IPython.display import Image
        return Image(url=self._name + '.svg')._repr_html_()

    def _repr_latex_(self):
        if self._inlined:
            return '\\begin{tikzpicture}' + self._content + '\\end{tikzpicture}'
        else:
            return f"\\includegraphics{{{self._name}.pdf}}"


import re

pattern = re.compile(r'\s+')
style = """
pre { background-color: #FDF6E3; }
.kw { color: #268BD2; }/*Keyword*/
.dt { color: #268BD2; }/*Data type*/
.dv { color: #D33682; }/*Decimal*/
.bn { color: #D33682; }/*BaseN value*/
.fl { color: #D33682; }/*Float*/
.ch { color: #DC322F; }/*Char*/
.st { color: #2AA198; }/*String*/
.co { color: #93A1A1; }/*Comment*/
.ot { color: #A57800; }/*Other*/
.at { color: #268BD2; }/*Attribute*/
.al { color: #CB4B16; font-weight: bold; }/*Alert*/
.fu { color: #268BD2; }/*Function*/
.re { }/*Region marker*/
.er { color: #D30102; font-weight: bold; }/*Error*/
.cf { font-weight: bold; }
""".strip()
style = '<style>' + re.sub(pattern, '', ''.join(style.split('\n'))) + '</style>'


class Style(BlockTag):
    def __init__(self, *children):
        super().__init__(children, 'style', '', raw=True)

    def _repr_latex_(self):
        return ''


class Pre(BlockTag):
    def __init__(self, *children):
        super().__init__(children, 'pre', 'verbatim', raw=True)


class Code:
    def __init__(self, code, lang):
        self.code = code
        self.lang = lang

    def _repr_html_(self):
        html = Pyblish.format(f"```{self.lang}\n{self.code}\n```", 'markdown', 'html')
        return style + html

    def _repr_latex_(self):
        Pyblish.format(f"```{self.lang}\n{self.code}\n```", 'markdown', 'latex')


ipynb = """                                                                        
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "id": "ccad6a9d-003f-4a2c-a592-70d40cd22e76",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": %STREAM%
    }
   ],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.16"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
"""


class Stream():
    def __init__(self, stream):
        self.stream = stream

    def _repr_latex_(self):
        import json
        stream = json.dumps(list(map(lambda it: it + '\n', self.stream)))
        return Pyblish.format(ipynb.replace('%STREAM%', stream), 'ipynb', 'latex')

    def _repr_html_(self):
        import json
        stream = json.dumps(list(map(lambda it: it + '\n', self.stream)))
        return '<samp>' + Pyblish.format(ipynb.replace('%STREAM%', stream), 'ipynb', 'html') + '</samp>'

    def __repr__(self):
        return ''


class FigCaption(InlineTag):
    def __init__(self, *children):
        super().__init__(children, 'figcaption', 'caption')


class Caption(InlineTag):
    def __init__(self, *children):
        super().__init__(children, 'caption', 'caption')


def debug(metadata, paths):
    import os
    os.makedirs('target/debug', exist_ok=True)
    Pyblish.format_from_files(paths, 'target/debug/output.json', 'ipynb', 'json', '--metadata-file', metadata)
    Pyblish.format_from_files(paths, 'target/debug/output.tex', 'ipynb', 'latex', '--metadata-file', metadata)


def release(metadata, paths, output):
    Pyblish.format_from_files(paths, output, 'ipynb', 'latex', '--metadata-file', metadata)
    call(['latexmk', '-pdf', output])
    call(['latexmk', '-c', output])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='builder',
        description='compile paper.iypnb and paper.yml to CP publication paper'
    )
    parser.add_argument('metadata')
    parser.add_argument('path', nargs='+')
    parser.add_argument('-r', '--release', action='store_true')
    parser.add_argument('-o', '--output')
    args = parser.parse_args()
    Pyblish.configure(args.metadata)
    if args.release:
        release(args.metadata, args.path, args.output)
    else:
        debug(args.metadata, args.path)
