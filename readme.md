# CopyAsHtml
This is a fork of [ExportHtml](https://github.com/facelessuser/ExportHtml).

This plugin allows you copy your code in HTML format to preserve its syntax highlighting.
It uses Sublime's theme colors and font styles.

\* For the moment, it only supports Windows. Pull requests are welcome.

## Install

_Not yet_: Use the **Sublime Package Control** and search for `Copy as HTML`.

or

Download this repo and place the whole folder in Sublime's `Packages` directory.

Sublime will automacitally download the dependencies and when it's done, restart Sublime.

## Usage

Just choose `Copy as HTML` from the context menu.

You can also bind the command to a key combination, for example:

```js
{
    	{ "keys": ["ctrl+shift+c"], "command": "copy_as_html" }
}
```

Tip: Use it with [Snipaste](https://snipaste.com). :wink:

## Credits
- [ExportHtml](https://github.com/facelessuser/ExportHtml)
- [SublimeHighlight](https://github.com/n1k0/SublimeHighlight)
- [PrintHtml](https://github.com/agibsonsw/PrintHtml)

## License
MIT
