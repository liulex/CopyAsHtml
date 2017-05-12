"""
Licensed under MIT.

Copyright (C) 2012  Andrew Gibson <agibsonsw@gmail.com>
Copyright (c) 2012 - 2017 Isaac Muse <isaacmuse@gmail.com>
Copyright (C) 2017  Le Liu

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
import sublime
import sublime_plugin
from os import path
import tempfile
import re
import CopyAsHtml.lib.desktop as desktop
from CopyAsHtml.lib.color_scheme_matcher import ColorSchemeMatcher
from CopyAsHtml.lib.color_scheme_tweaker import ColorSchemeTweaker
from CopyAsHtml.lib.notify import notify
import jinja2

if desktop.get_desktop() == 'Windows':
    import CopyAsHtml.winclip as winclip

PACKAGE_SETTINGS = "CopyAsHtml.sublime-settings"

# HTML Code
HTML_HEADER = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<HTML><HEAD>
<BODY><!--StartFragment-->
<style type="text/css">
%(css)s
</style>
'''

BODY_START = '<pre class="code_page code_text">'

LINE = '<div>%(code)s\n</div>'    

CODE = '<span class="%(class)s" style="background-color: %(highlight)s; color: %(color)s;">%(content)s</span>'

DIVIDER = '<span style="color: %(color)s">\n...\n\n</span>'

BODY_END = '</pre><!--EndFragment--></BODY></HTML>'


def getcss(options):
    """Get CSS file."""

    code = ""
    settings = sublime.load_settings(PACKAGE_SETTINGS)
    # user_vars = settings.get("user_css_vars", {})
    export_css = settings.get("export_css", 'Packages/CopyAsHtml/css/export.css')

    try:
        code = sublime.load_resource(export_css)
        code = jinja2.Environment().from_string(code).render(var=options)
    except Exception:
        pass

    return code.replace('\r', '')


class CopyAsHtmlCommand(sublime_plugin.WindowCommand):
    """CopyAsHtml command."""

    def run(self, **kwargs):
        """Run command."""

        view = self.window.active_view()
        if view is not None:
            CopyAsHtml(view).run(**kwargs)


class OpenHtml:
    """Open either a temporary HTML."""

    def __init__(self, file_name):
        """Initialize."""

        self.file_name = file_name

    def __enter__(self):
        """Setup HTML file."""

        self.file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=self.file_name)
        return self.file

    def __exit__(self, type, value, traceback):
        """Tear down HTML file."""

        self.file.close()


class CopyAsHtml(object):
    """CopyAsHtml."""

    def __init__(self, view):
        """Initialization."""

        self.view = view

    def process_inputs(self, **kwargs):
        """Process the user inputs."""

        return {
            "multi_select": bool(kwargs.get("multi_select", False)),
            "filter": kwargs.get("filter", ""),
            "disable_nbsp": kwargs.get('disable_nbsp', False)
        }

    def setup(self, **kwargs):
        """Get get general document preferences from sublime preferences."""

        eh_settings = sublime.load_settings(PACKAGE_SETTINGS)
        settings = sublime.load_settings('Preferences.sublime-settings')
        self.font_size = settings.get('font_size', 10)
        self.font_face = settings.get('font_face', 'Consolas')
        self.tab_size = settings.get('tab_size', 4)
        self.padd_top = settings.get('line_padding_top', 0)
        self.padd_bottom = settings.get('line_padding_bottom', 0)
        self.char_limit = int(eh_settings.get("valid_selection_size", 4))
        self.bground = ''
        self.fground = ''
        self.disable_nbsp = kwargs["disable_nbsp"]
        self.sels = []
        if kwargs["multi_select"]:
            self.multi_select = self.check_sel()
        else:
            self.multi_select = False
        self.size = self.view.size()
        self.pt = 0
        self.end = 0
        self.curr_row = 0
        self.ebground = self.bground
        self.plain_text = ''

        # Get color scheme
        scheme_file = self.view.settings().get('color_scheme')

        self.csm = ColorSchemeMatcher(
            scheme_file,
            color_filter = (lambda x: ColorSchemeTweaker().tweak(x, kwargs["filter"]))
        )

        self.fground = self.csm.get_special_color('foreground', simulate_transparency=True)
        self.bground = self.csm.get_special_color('background', simulate_transparency=True)

    def setup_print_block(self, curr_sel, multi=False):
        """Determine start and end points and whether to parse whole file or selection."""

        # Nothing is selected. Set the range to the full line.
        if not multi and (curr_sel.empty() or curr_sel.size() <= self.char_limit):
            curr_sel = self.view.full_line(curr_sel)

        self.size = curr_sel.end()
        self.pt = curr_sel.begin() 
        self.end = self.pt + 1
        self.curr_row = self.view.rowcol(self.pt)[0] + 1
        self.start_line = self.curr_row

    def check_sel(self):
        """Check if selection is a multi-selection."""

        multi = False
        for sel in self.view.sel():
            if not sel.empty() and sel.size() >= self.char_limit:
                multi = True
                self.sels.append(sel)
        return multi

    def print_line(self, line, num):
        """Print the line."""

        html_line = LINE % {
            "code": line
        }

        return html_line

    def write_header(self, html):
        """Write the HTML header."""

        header_vars = {
            "css": getcss(
                {
                    "font_size": str(self.font_size),
                    "font_face": '"' + self.font_face + '"',
                    "page_bg": self.bground,
                    "body_fg": self.fground
                }
            )
        }

        header = HTML_HEADER % header_vars

        html.write(header)

    def convert_view_to_html(self, html):
        """Begin conversion of the view to HTML."""

        for line in self.view.split_by_newlines(sublime.Region(self.pt, self.size)):
            self.size = line.end()
            self.line_start = line.begin()
            if self.curr_row > 1:
                self.line_start -= 1
            empty = not bool(line.size())
            line = self.convert_line_to_html(empty)
            html.write(self.print_line(line, self.curr_row))
            self.curr_row += 1

    def html_encode(self, text, start_pt=None):
        """Format text to HTML."""
        encode_table = {
            '&': '&amp;',
            '>': '&gt;',
            '<': '&lt;',
            '\t': ' ' * self.tab_size,
            '\n': ''
        }

        if self.disable_nbsp:
            return ''.join(
                encode_table.get(c, c) for c in text
            ).encode('ascii', 'xmlcharrefreplace').decode("utf-8")
        else:
            return re.sub(
                r'(?<=^) | (?= )' if start_pt is not None and start_pt == self.line_start else r' (?= )',
                lambda m: '&nbsp;' * len(m.group(0)),
                ''.join(
                    encode_table.get(c, c) for c in text
                ).encode('ascii', 'xmlcharrefreplace').decode("utf-8")
            )

    def format_text(self, line, text, color, bgcolor, style, empty):
        """Format the text."""

        if not style:
            style == 'normal'

        if empty:
            text = '&nbsp;' if not self.disable_nbsp else ' '
        else:
            style += " real_text"

        if bgcolor is None:
            bgcolor = self.bground

        code = CODE % {"highlight": bgcolor, "color": color, "content": text, "class": style}

        line.append(code)

    def convert_line_to_html(self, empty):
        """Convert the line to its HTML representation."""

        line = []

        while self.end <= self.size:
            # Get text of like scope
            scope_name = self.view.scope_name(self.pt)
            while self.view.scope_name(self.end) == scope_name and self.end < self.size:
                self.end += 1
            color_match = self.csm.guess_color(scope_name)
            color = color_match.fg_simulated
            style = color_match.style
            bgcolor = color_match.bg_simulated

            region = sublime.Region(self.pt, self.end)
            
            # Collect plain text
            text = self.view.substr(region)
            self.plain_text += text

            # Normal text formatting
            tidied_text = self.html_encode(text, region.begin())
            self.format_text(line, tidied_text, color, bgcolor, style, empty)

            # Continue walking through line
            self.pt = self.end
            self.end = self.pt + 1

        # Get the color for the space at the end of a line
        if self.end < self.view.size():
            end_key = self.view.scope_name(self.pt)
            color_match = self.csm.guess_color(end_key)
            self.ebground = color_match.bg_simulated

        # Join line segments
        return ''.join(line)

    def write_body(self, html):
        """Write the body of the HTML."""

        processed_rows = ""
        html.write(BODY_START)

        # Convert view to HTML
        if self.multi_select:
            count = 0
            total = len(self.sels)
            for sel in self.sels:
                self.setup_print_block(sel, multi=True)
                processed_rows += "[" + str(self.curr_row) + ","
                self.convert_view_to_html(html)
                count += 1
                processed_rows += str(self.curr_row) + "],"

                if count < total:
                    html.write(DIVIDER % {"color": self.fground})
        else:
            self.setup_print_block(self.view.sel()[0])
            processed_rows += "[" + str(self.curr_row) + ","
            self.convert_view_to_html(html)
            processed_rows += str(self.curr_row) + "],"

        html.write(BODY_END)

    def open_html(self, x):
        """Open html file."""
        
        return tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=x)

    def run(self, **kwargs):
        """Run command."""

        inputs = self.process_inputs(**kwargs)
        self.setup(**inputs)

        html_file = ".html"

        with OpenHtml(html_file) as html:
            self.write_header(html)
            self.write_body(html)
            
            # Set clipboard
            html.seek(0)

            if desktop.get_desktop() == 'Windows':
                #TODO put plain text as well
                winclip.Copy(html.read(), 'html', self.plain_text)
            else:
                #TODO other platforms...
                sublime.set_clipboard(self.plain_text)
            
            notify("HTML copied to clipboard")

def plugin_loaded():
    """Setup plugin."""

    pass
