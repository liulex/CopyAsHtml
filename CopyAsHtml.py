"""
Licensed under MIT.

Copyright (C) 2012  Andrew Gibson <agibsonsw@gmail.com>
Copyright (c) 2012 - 2017 Isaac Muse <isaacmuse@gmail.com>
Copyright (C) 2017 - 2019 Le Liu
Copyright (C) 2019  hyrious

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from sublime import *
from sublime_plugin import *
from plistlib import readPlistFromBytes
from cgi import escape
import colorsys
import re
from .lib import desktop
if desktop.get_desktop() == 'Windows':
    from .lib import winclip


HTML_HEADER = '''\
<!DOCTYPE html><HTML><HEAD><meta charset="UTF-8"></HEAD><BODY><!--StartFragment-->\
<style type="text/css">\
pre {font-family: %(fface)s, Monospace; font-size: %(fsize)dpt; background: %(bcolor)s;}\
%(styles)s</style><pre>'''

HTML_END = '\n</pre><!--EndFragment--></BODY></HTML>'


def sel0_or_all(view):
    r = view.sel()[0]
    return Region(0, view.size()) if r.empty() else r


def css(style):
    s = 'color:%s;' % style['foreground']
    t = [x for x in ['bold', 'italic'] if style[x]]
    if t:
        s += 'font-style: %s;' % ' '.join(t)
    return s


def lex(view):
    temp = None
    colors = set()
    tokens = []
    r = sel0_or_all(view)
    for i in range(r.begin(), r.end()):
        if view.substr(i).isspace():
            continue
        s = view.style_for_scope(view.scope_name(i))
        t = css(s)
        if temp != t:
            temp = t
            tokens.append((i, temp))
            colors.add(temp)
    colors = list(colors)
    beg = r.begin()
    temp = None
    ret = []
    for i, t in tokens:
        if temp is None:
            temp = t
        else:
            text = view.substr(Region(beg, i))
            ret.append((text, colors.index(temp)))
            temp = t
            beg = i
    if beg < r.end():
        text = view.substr(Region(beg, r.end()))
        ret.append((text, colors.index(temp)))
    return colors, ret


def hsl_to_hex(color):
    if color.startswith('hsl('):
        # e.g. hsl(210, 15%, 24%)
        hsl = [int(s) for s in re.findall(r'\d+', color)]
        if len(hsl) == 3:
            rgb = colorsys.hls_to_rgb(hsl[0] / 360.0, hsl[2] / 100.0, hsl[1] / 100.0)
            color = '#%02x%02x%02x' % tuple(round(x * 255) for x in rgb)
    return color


def get_background_color(view):
    background = 'transparent'
    source_file = view.style_for_scope('')['source_file']
    if source_file.endswith('.tmTheme'):
        dic = readPlistFromBytes(load_binary_resource(source_file))
        if 'settings' in dic:
            for setting in dic['settings']:
                if 'settings' in setting and 'scope' not in setting:
                    subsettings = setting['settings']
                    if 'background' in subsettings:
                        background = subsettings['background']
    elif source_file.endswith('.sublime-color-scheme'):
        dic = decode_value(load_resource(source_file))
        if 'globals' in dic:
            globa = dic['globals']
            if 'background' in globa:
                background = globa['background']
                if background.startswith('var('):
                    key = background[4:-1]
                    if 'variables' in dic:
                        variables = dic['variables']
                        if key in variables:
                            background = variables[key]
    return hsl_to_hex(background)


class CopyAsHtmlCommand(TextCommand):
    def run(self, edit):
        view = self.view
        background = get_background_color(view)
        colors, tokens = lex(view)

        settings = sublime.load_settings('Preferences.sublime-settings')
        font_size = settings.get('font_size', 10)
        font_face = settings.get('font_face', 'Consolas')

        custom_styles = ''
        for i, c in enumerate(colors):
            custom_styles += '.c%d { %s }' % (i, c)

        html = HTML_HEADER % {"bcolor": background, "fsize": font_size,
                              "fface": font_face, "styles": custom_styles}
        plain_text = ''
        for t, i in tokens:
            html += '<span class=c%d>%s</span>' % (i, escape(t))
            plain_text += t
        html += HTML_END

        if desktop.get_desktop() == 'Windows':
            # print(html)
            winclip.Copy(html, 'html', plain_text)
        else:
            #TODO other platforms...
            sublime.set_clipboard(html)
