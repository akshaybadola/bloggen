from typing import List, Dict, Optional, Union
import os
import re
import sys
import json
import shutil
import tempfile
from pathlib import Path
from subprocess import Popen, PIPE
from types import SimpleNamespace
from bs4 import BeautifulSoup
from common_pyutil.system import Semver

from .components import (title_file_string, snippet_string,
                         article_snippet_with_category,
                         snippet_string_with_category,
                         about_snippet, about_string)

from .util import (find_bibliographies, replace_metadata, print_, print_1,
                   print_2, compile_sass, shell_command_to_string)



class BlogGenerator:
    """A `Pandoc <https://github.com/jgm/pandoc>` and markdown based blog generator.

    Args:
        input_dir: Input directory for the blog content
        output_dir: Output directory for the blog content
        themes_dir: Themes directory.
                    The themes directory should contain the themes and each
                    theme should have a `templates` and `assets` dir.
        theme: Name of the theme. The directory with that name should be
                present in the `themes_dir`
        csl_dir: Directory containing CSL files
        bib_dirs: Directories containing bibtex files
        exclude_dirs: Directories to exclude while scanning for content
        citation_style: Citation style to use.
                        The CSL file with that name should be present in `cls_dir`.

    It:
        1. Creates blog_output directory if it doesn't exist
        2. Creates the folder structure
           - Copy assets folder
           - Generate research, programming, other_blog, links, about_me etc. folders as required
           - Get info from file metadata
           - Check files for changes and update
        3. Generates and updates the posts and indices.
           - Generate each post from corresponding markdown with pandoc
           - Update index, tags and categories file each time
           - Delete obsolete html files and folders
        4. TODO: Handle additional files (like images and stuff for the generated html files)
        5. Bundles and minifys the html (with external plugin)
        6. TODO: Maybe filter by multiple tags with JS
    """
    def __init__(self, input_dir: Path, output_dir: Path, themes_dir: Path,
                 csl_dir: Path, variables: Path, theme: str, bib_dirs: List[str],
                 exclude_dirs: List[str], citation_style: str, dry_run: bool,
                 contact=Dict[str, str], pandoc_config=Dict[str, str]):
        print_("Checking Generator Options:")
        self.dry_run = dry_run
        self.input_dir = self.check_exists(input_dir)
        self.output_dir = self.ensure_dir(output_dir)
        self.theme = self.check_exists(themes_dir.joinpath(theme))
        self.templates_dir = self.check_exists(self.theme.joinpath("templates"))
        with open(self.check_exists(variables)) as f:
            self.variables = json.load(f)
        # TODO: Citations can be optional
        self.csl_dir = self.check_exists(csl_dir)
        self.assets_dir = self.check_exists(self.theme.joinpath("assets"))
        self.bib_dirs = bib_dirs
        self.hosted_paths = ["assets", "tags", ".git"]
        # FIXME: This is unused
        self.exclude_dirs = exclude_dirs
        self.files_data_file = self.input_dir.joinpath(".files_data")
        self.pandoc_config = pandoc_config
        self.contact = contact
        self.set_pandoc_opts()
        self.generate_opts(citation_style)

    def set_pandoc_opts(self):
        self.pandoc_cmd = self.check_exists(
            Path(self.pandoc_config.get("pandoc_executable", "/usr/bin/pandoc")))
        out, err = shell_command_to_string(str(self.pandoc_cmd) + " --version")
        if not err:
            self.pandoc_version = out.split()[1]
        else:
            print_1("Pandoc error.")
            sys.exist(1)
        print_1(f"Will use pandoc {self.pandoc_cmd}, version {self.pandoc_version}")

    def generate_opts(self, citation_style):
        self.snippet_cache: Dict[str, SimpleNamespace] = {}
        self.general_opts = " ".join(["-r markdown+simple_tables+table_captions+" +
                                      "yaml_metadata_block+fenced_code_blocks+raw_html",
                                      "-t html"])
        if Semver(self.pandoc_version).smaller_than("2.14"):
            self.reader_opts = "--filter=pandoc-citeproc"
        else:
            self.reader_opts = "--citeproc"
        self.index_template = self.check_exists(self.templates_dir.joinpath("index.template"))
        self.post_template = self.check_exists(self.templates_dir.joinpath("post.template"))
        self.writer_opts = " ".join([f"--template={self.index_template}",
                                     f"-V templates_dir={self.templates_dir}",
                                     "--toc"])
        self.csl_file = self.csl_dir.joinpath(citation_style + ".csl")
        if not self.csl_file.exists():
            raise FileNotFoundError(self.csl_file)
        self.citation_opts = f"--csl={self.csl_file}"
        self.index_cmd = " ".join(map(str, [self.pandoc_cmd, self.general_opts,
                                            self.reader_opts, self.writer_opts.replace("--toc", ""),
                                            self.citation_opts]))
        self.tag_cmd = self.index_cmd
        self.category_cmd = self.index_cmd
        self.post_cmd = " ".join(map(str, [self.pandoc_cmd, self.general_opts,
                                           self.reader_opts, self.writer_opts,
                                           self.citation_opts])).replace(
                                               "index.template", "post.template")
        print("\n")

    def check_exists(self, path: Path) -> Path:
        print_1(f"Checking for {path}")
        if not path.exists():
            raise FileNotFoundError(path)
        else:
            return path

    def ensure_dir(self, path: Path) -> Path:
        if path.exists() and not path.is_dir():
            raise AttributeError(f"{path} is supposed to be a directory")
        elif not path.exists():
            if self.dry_run:
                print_1(f"Not creating {path} as dry run")
            else:
                os.mkdir(path)
        return path

    @property
    def index_data(self) -> List[Dict[str, str]]:
        return self._index_data

    @index_data.setter
    def index_data(self, x: List[Dict[str, str]]):
        self._index_data = x

    def update_styles(self, out_dir: Path):
        self.copy_assets_dir(out_dir)

    def run_pipeline(self, out_dir: Path, files_data: Dict[str, Dict],
                     preview: bool, update_all: bool, input_pattern: str):
        out_dir = self.ensure_dir(out_dir)
        if preview:
            print("Generating Preview:")
            if out_dir != self.output_dir:
                self.copy_output_to_preview(out_dir)
        else:
            print("Building Pages:")
        self.copy_assets_dir(out_dir)
        self.load_titles(out_dir)
        self.files_data = files_data
        self.update_category_and_post_pages(out_dir)
        if self.index_data:     # only if updates needed
            self.generate_index_page(out_dir, self.index_data)
        self.generate_tag_pages(out_dir)
        self.generate_other_pages(out_dir)
        self.cleanup(out_dir)

    def copy_output_to_preview(self, preview_dir):
        if self.dry_run:
            print_1("Not copying data from {self.output_dir} to {preview_dir} as dry run")
        else:
            for x in self.output_dir.iterdir():
                if x.is_dir() and x.name != ".git":
                    shutil.copytree(self.output_dir.joinpath(x.name),  # type: ignore
                                    preview_dir.joinpath(x.name), dirs_exist_ok=True)
                elif x.is_file():
                    shutil.copy(self.output_dir.joinpath(x.name),
                                preview_dir.joinpath(x.name))

    def copy_assets_dir(self, out_dir: Path):
        """Copy the assets """
        if self.dry_run:
            print_1(f"Not copying {self.assets_dir} to {out_dir} as dry run")
        else:
            compile_sass(self.assets_dir)
            print_1(f"Copying {self.assets_dir} to {out_dir}")
            out_assets_dir = os.path.join(out_dir, str(self.assets_dir).split("/")[-1])
            shutil.copytree(self.assets_dir, out_assets_dir, dirs_exist_ok=True)  # type: ignore
            if abouts := self.variables.get("about", None):
                with open(Path(out_assets_dir).joinpath("js/about.js"), "w") as f:
                    f.write(about_string(abouts))

    def load_titles(self, out_dir):
        print_1("Generating title files")
        self.titles = self.variables["titles"]
        # tf_string = title_file_string()
        for k, v in self.titles.items():
            print_1(f"Generated titles for {k}")
            if self.dry_run:
                print_1(f"Not writing titles for {k} as dry run")
            else:
                with open(os.path.join(out_dir, f"assets/js/{k}_titles.js"), "w") as f:
                    # f.write(tf_string.replace("$TITLES$", str(v)))
                    f.write(title_file_string(v))

    def generate_post_page(self, post_file, metadata):
        if "bibliography" in metadata:
            bib_files = find_bibliographies(metadata["bibliography"], self.bib_dirs)
            with tempfile.NamedTemporaryFile(mode="r+", prefix="bloggen-") as tp:
                with open(post_file) as pf:
                    post = pf.read()
                metadata["bibliography"] = bib_files
                tp.write(replace_metadata(post, metadata))
                tp.flush()
                p = Popen(f"{self.post_cmd} {tp.name}",
                          shell=True, stdout=PIPE, stderr=PIPE)
                out, err = p.communicate()
        else:
            p = Popen(f"{self.post_cmd} {post_file}",
                      shell=True, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
        if err:
            print_1(err)
        page = out.decode("utf-8")
        date = metadata["date"]
        tags = metadata["tags"].split(",")
        tags = [t.strip().replace(" ", "_").lower() for t in tags
                if t.strip().replace(" ", "_").lower() not in self.categories]
        tags = " ".join([f"<a class=\"tag\" href='../tags/{tag}.html'>{tag}</a>" for tag in tags])
        category = metadata["category"]
        edited = None
        if "edited" in metadata:
            edited = metadata["edited"]
        page = page.replace("$ADD_DATA$", f'<span>Posted on: {date},' +
                            (f' Edited on: {edited},' if edited else '') + ' in Category:' +
                            f' <a class="category" href="../{category}.html">{category}</a>' +
                            (f", tags: {tags}" if tags else "") + "</span>")
        page = self.fix_title(category, page, prefix=True)
        return page

    # TODO: code formatting for programming stuff
    def generate_posts(self, out_dir):
        for fname, fval in self.files_data.items():
            metadata = fval["metadata"]
            if "category" in metadata:  # only posts have categories
                category = metadata["category"]
                out_file = os.path.join(out_dir, category, fname.replace(".md", ".html"))
                if fval["update"] or not os.path.exists(out_file):
                    print_1(f"Generating post {fname}")
                    page = self.generate_post_page(os.path.join(self.input_dir, fname),
                                                   metadata)
                    page = self.add_about(out_dir, page, True)
                    if self.dry_run:
                        print_1(f"Not writing post page {fname}.html as dry run")
                    else:
                        with open(out_file, "w") as f:
                            f.write(page)

    def update_category_and_post_pages(self, out_dir):
        categories = {}
        for fname, fval in self.files_data.items():
            meta = fval["metadata"]
            # page without category is a root page
            if "category" in meta:
                if meta["category"] not in categories:
                    categories[meta["category"]] = []
                categories[meta["category"]].append(fname)
        self.categories = [*categories.keys()]
        for cat, pages in categories.items():
            if not os.path.exists(os.path.join(out_dir, cat)):
                os.mkdir(os.path.join(out_dir, cat))
            pages.sort(key=lambda x: self.files_data[x]["metadata"]["date"], reverse=True)
        self.generate_posts(out_dir)
        index_data = []
        for cat, pages in categories.items():
            # - filter by tags may only work with javascript
            # - page.insert snippet with a <next> for let's say 5-6 results per page
            # if noscript then show everything (no <next> tags)
            data = []
            for i, page in enumerate(pages):
                temp = {}
                temp["date"] = self.files_data[page]["metadata"]["date"]
                tags = self.files_data[page]["metadata"]["tags"]
                tags = [t.strip().lower() for t in tags.split(",")
                        if t.strip().lower() not in self.categories]
                temp["tags"] = [t.replace(" ", "_").lower() for t in tags]
                html_file = os.path.join(out_dir, cat, page.replace(".md", ".html"))
                temp["snippet"] = self.get_snippet_content(html_file)
                temp["path"] = "/".join([cat, page.replace(".md", ".html")])
                data.append(temp)
                if not i:       # ignore heading
                    index_data.append({**temp, "category": cat})
            print_1(f"Generating category {cat} page")
            self.generate_category_page(out_dir, cat, data)
        self.index_data = index_data

    def get_snippet_content(self, html_file: str):
        if html_file not in self.snippet_cache:
            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), features="lxml")
            heading = soup.find("title").text
            paras = soup.findAll("p")
            text: List[str] = []
            while paras and len(text) <= 70:
                para = paras.pop(0)
                text.extend(para.text.split(" "))
            self.snippet_cache[html_file] = SimpleNamespace(
                **{"heading": heading, "text": " ".join(text)})
        return self.snippet_cache[html_file]

    # NOTE: modify this to change index menu, rest should be similar
    # TODO: This should be generated from a config
    def menu_string(self, categories, path_prefix=""):
        menu = []
        for cat in categories:
            menu.append(f"<li><a href='{path_prefix}{cat}.html'>{cat.capitalize()}</a></li>")
        menu.extend([f"<li><a href='{path_prefix}links.html'>Links</a></li>",
                     f"<li><a href='{path_prefix}about.html'>About</a></li>"])
        # Home by default shows most recent one snippet from each category
        menu.insert(0, f"<li><a href='{path_prefix}index.html'>Home</a></li>")
        menu.insert(0, "<ul>")
        menu.append("</ul>")
        return "".join(menu)

    def fix_title(self, category, page, prefix=False):
        if category in self.titles:
            title_script_tag = f'<script type="text/javascript" ' +\
                f'src="{"../" if prefix else ""}assets/js/{category}_titles.js"></script>'
            page = page.replace("$TITLES_FILE$", title_script_tag)
            default_title = self.titles[category][0]
        else:
            print_1(f"Category {category} not in titles.json")
            print_1(f"Replacing with default_title")
            page = page.replace("$TITLES_FILE$", "")
            default_title = self.titles["index"][0]
        page = re.sub('<p><h1 align="center">(.*)</h1></p>', '<h1 align="center">\\1</h1>', page)
        return re.sub('<h1 class="title">.*</h1>',
                      f'<h1 class="title">{default_title}</h1>', page)

    def add_about(self, out_dir: Path, page, prefix=False):
        about_path = "../about.html"
        if "img_path" in self.contact:
            img_path = Path(self.contact["img_path"]).absolute()
            out_path = out_dir.joinpath("assets/img/", "photo" + img_path.suffix)
            shutil.copy(img_path, out_path)
        else:
            out_path = Path("")
        if self.variables.get("about", None):
            about_script_tag = f'<script type="text/javascript" ' +\
                f'src="{"../" if prefix else ""}assets/js/about.js"></script>'
        else:
            about_script_tag = ""
        name = self.contact["name"]
        about_str = self.contact.get("about", "") or self.variables.get("about", [""])[0]
        if not about_str and not about_script_tag:
            print_1("Empty about string")
            about_str = "I'm a cool guy (I think)"
        img_src_path = os.path.join(f'{"../" if prefix else ""}assets/img/', out_path.name)
        about_ = about_script_tag + about_snippet(about_path, img_src_path,
                                                  name, about_str, self.contact)
        return page.replace("$ABOUT$", about_)

    # TODO: I was thinking to use pypandoc, but that calls subprocess anyway
    #       instead of interfacing with haskell libs. Better to write my own
    #       input and output parser for pandoc, similar to pandocwatch
    def generate_index_page(self, out_dir, data):
        print_1(f"Generating index page")
        p = Popen(f"{self.index_cmd} {self.input_dir}/index.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print_1(err)
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        index_path = os.path.join(out_dir, "index.html")
        snippets = []
        data.sort(key=lambda x: x["date"], reverse=True)
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = " ".join([f"<a class='tag' href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            category = d["category"]
            snippets.append(snippet_string_with_category(snippet, path, date, category, tags))
            # snippets.append(article_snippet_with_category(snippet, path, date, category, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        page = self.add_about(out_dir, page)
        page = self.fix_title("index", page)
        if self.dry_run:
            print_1(f"Not writing page {index_path} as dry run")
        else:
            with open(index_path, "w") as f:
                f.write(page)

    # TODO: JS 5-6 snippets at a time with <next> etc.
    def generate_category_page(self, out_dir, category, data):
        p = Popen(f"{self.category_cmd} {self.input_dir}/{category}.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print_1(err)
        if 'not exist' in err.decode("utf-8"):
            print_1(f"File {category}.md doesn't exist. Cannot continue.")
            sys.exit(1)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        snippets = []
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = " ".join([f"<a class=\"tag\" href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            snippets.append(snippet_string(snippet, path, date, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        page = self.add_about(out_dir, page)
        page = self.fix_title(category, page)
        if self.dry_run:
            print_1(f"Not writing page {category}.html as dry run")
        else:
            with open(os.path.join(out_dir, f"{category}.html"), "w") as f:
                f.write(page)

    def generate_tag_pages(self, out_dir):
        # TODO: Exclude categories from tags
        tag_pages_dir = os.path.join(out_dir, "tags")
        p = Popen(f"{self.tag_cmd} {self.input_dir}/tag.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print_1(err)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories, "../")
        page = page.replace("$INDEX_TOC$", menu_string)
        page = page.replace("href=\"assets/", "href=\"../assets/")
        page = page.replace("src=\"assets/", "src=\"../assets/")
        all_tags = {}
        for fname, fval in self.files_data.items():
            if "category" in fval["metadata"]:  # only posts
                tags = fval["metadata"]["tags"]
                tags = [t.strip().replace(" ", "_").lower() for t in tags.split(",")
                        if t not in self.categories]
                for tag in tags:
                    if tag not in all_tags:
                        all_tags[tag] = []
                    all_tags[tag].append([fname, fval["metadata"]["category"],
                                          fval["metadata"]["date"]])
        if not os.path.exists(tag_pages_dir):
            os.mkdir(tag_pages_dir)
        for tag, files in all_tags.items():
            tag_page = page.replace("$TAG$", tag)
            snippets = []
            for fname, category, date in files:
                _fname = fname.replace(".md", ".html")
                snippet = self.get_snippet_content(os.path.join(
                    out_dir, category, fname.replace(".md", ".html")))
                path = f"../{category}/{_fname}"
                snippets.append(snippet_string_with_category(snippet, path, date, category,
                                                             cat_path_prefix="../"))
            tag_page = tag_page.replace("$SNIPPETS$", "\n".join(snippets))
            tag_page = self.add_about(out_dir, tag_page, True)
            tag_page = self.fix_title("index", tag_page, True)
            if self.dry_run:
                print_1(f"Not writing page {tag}.html as dry run")
            else:
                with open(os.path.join(tag_pages_dir, f"{tag}.html"), "w") as f:
                    f.write(tag_page)
        self.all_tags = all_tags

    def generate_other_pages(self, out_dir):
        self.generate_about_page(out_dir)
        self.generate_links_page(out_dir)
        self.generate_quotes_page(out_dir)

    def generate_about_page(self, out_dir):
        pass

    def generate_links_page(self, out_dir):
        pass

    def generate_quotes_page(self, out_dir):
        pass

    def cleanup(self, out_dir):
        """This function:
            1. Deletes obsolete posts
            2. Deletes obsolete tag pages
            3. Deletes obsolete category pages and folders
        """
        # delete obsolete category folders
        cat_dirs = [*self.categories, *self.hosted_paths]
        for o in out_dir.iterdir():
            if o.is_dir() and o.name not in cat_dirs:
                if self.dry_run:
                    print_1(f"NOT deleting obsolete category folder {o} as dry run")
                else:
                    print_1(f"Deleting obsolete category folder {o}")
                    shutil.rmtree(str(o.absolute()))
            elif (o.is_file() and o.suffix == ".html"
                  and o.name != "index.html" and o.stem not in cat_dirs):
                if self.dry_run:
                    print_1(f"NOT deleting obsolete file {o} as dry run")
                else:
                    print_1(f"Deleting obsolete file {o}")
                    os.remove(o)
        for cat in self.categories:
            # Raise error if some category was not written
            if not out_dir.joinpath(cat).exists():
                raise FileNotFoundError(out_dir.joinpath(cat))
            # Delete obsolete posts
            for out_path in out_dir.joinpath(cat).iterdir():
                if out_path.stem + ".md" not in self.files_data:
                    if self.dry_run:
                        print_1(f"NOT removing obsolete file {out_path} as dry run")
                    else:
                        print_1(f"Removing obsolete file {out_path}")
                        os.remove(out_path)
        for tag in out_dir.joinpath("tags").iterdir():
            if tag.stem not in self.all_tags:
                if self.dry_run:
                    print_1(f"NOT removing obsolete tag {tag} as dry run")
                else:
                    print_1(f"Removing obsolete tag {tag}")
                    os.remove(tag)
