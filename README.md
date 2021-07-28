# Simple Blog Generation with Pandoc

Simple and effective Blog Generator with Pandoc. Can read yaml metadata from
headers and generate meta pages with `tags` and `categories` with corresponding
TOC. The LITE version can be rendered with a text based browser without JS
also.

~~A shinier React version will be added soon.~~

## Purpose

The primary purpose is managing conversions from org/markdown to
html/pdf. However I have a custom setup for org mode for managing all my
readings, writings and time tracking, and current org export backends don't give
me that flexibility. This toolchain depends on pandoc which is a universal
converter and so more plugins for such things can be added easily.

I was thinking of added a React managed frontend but I feel now that is overkill
for a blog as there's nothing really dynamic in these articles. I might use such
components library on the full homepage (currently this is served at
blog.badola.dev and the homepage would be badola.dev), for demos or advanced
apps if needed but I don't think it's needed here.

I might more features to source management in the future and better
documentation for themes. Right now only the default theme works and that too is
pretty adhoc. See (https://github.com/akshaybadola.github.io) and
(https://blog.badola.dev) for how it looks finally.

## Roadmap

- Add tests
- Add file minimizer
- Add pagination
