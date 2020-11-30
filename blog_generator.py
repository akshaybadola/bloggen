import os
import re
import yaml
import json
import shutil
import hashlib
import argparse
import configparser
from subprocess import Popen, PIPE
from bs4 import BeautifulSoup
from types import SimpleNamespace


def title_file_string(titles):
    "Return string which will be used to generate titles from json"
    return f"""const titles = {titles};
const index = Math.floor(Math.random() * titles.length);
const title = titles[index];
document.title = title;
document.getElementById("header").children[0].textContent = title;"""


def snippet_string(snippet, path, date, tags=None):
    "Return string which will be used to generate snippets"
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p><br>
<p>Posted on: {date}""" + (f", tags: {tags}</p></div>" if tags else "</p></div>")


def snippet_string_with_category(snippet, path, date, category, tags=None, cat_path_prefix=""):
    """Return string which will be used to generate snippets with categories beneath it.
    Used for posts"""
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p><br>
<p>Posted on: {date}, in Category: <a href="{cat_path_prefix}{category}.html">{category}</a>""" +\
        (f", tags: {tags}</p></div>" if tags else "</p></div>")


class BlogGenerator:
    def __init__(self, input_dir, output_dir, layout_dir, csl_dir,
                 assets_dir, exclude_dirs):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.layout_dir = layout_dir
        self.csl_dir = csl_dir
        self.assets_dir = assets_dir
        # FIXME: This is unused
        self.exclude_dirs = exclude_dirs
        self.files_data = os.path.join(self.input_dir, ".files_data")
        self.tag_pages_dir = os.path.join(self.output_dir, "tags")
        self._snippet_cache = {}
        self.sanity_check()
        self.pandoc_cmd = "/usr/bin/pandoc"
        self.general_opts = " ".join(["-r markdown+simple_tables+table_captions+" +
                                      "yaml_metadata_block+fenced_code_blocks+raw_html",
                                      "-t html"])
        self.reader_opts = " ".join(["--filter=pandoc-citeproc"])
        self.writer_opts = " ".join(["--template=" +
                                     os.path.join(self.layout_dir, "index.template"),
                                     f"-V layout_dir={self.layout_dir}", "--toc"])
        # TODO: citation file can also be changed
        self.citation_opts = " ".join(["--csl=" + os.path.join(self.csl_dir, "ieee.csl")])
        self.index_cmd = " ".join([self.pandoc_cmd, self.general_opts,
                                   self.reader_opts, self.writer_opts.replace("--toc", ""),
                                   self.citation_opts])
        self.tag_cmd = self.index_cmd
        self.category_cmd = self.index_cmd
        self.post_cmd = " ".join([self.pandoc_cmd, self.general_opts,
                                  self.reader_opts, self.writer_opts,
                                  self.citation_opts]).replace(
                                      "index.template", "post.template")

    def run_pipeline(self, update_all):
        self.load_titles()
        self.check_for_changes(update_all)
        self.update_category_and_post_pages()
        if self.index_data:     # only if updates needed
            self.generate_index_page(self.index_data)
        self.generate_tag_pages()
        self.generate_other_pages()
        # preview and push?

    def load_titles(self):
        print("Loading titles and generating files")
        with open("blog_input/titles.json") as f:
            self.titles = json.load(f)
        # tf_string = title_file_string()
        for k, v in self.titles.items():
            print(f"Generated titles for {k}")
            with open(f"blog_output/assets/js/{k}_titles.js", "w") as f:
                # f.write(tf_string.replace("$TITLES$", str(v)))
                f.write(title_file_string(v))

    # NOTE:
    # The blog post processor should
    # 1. create blog_output directory if it doesn't exist
    # 2. create the folder structure
    #    - Copy assets folder (DONE)
    #    - Generate research, programming, other_blog, links, about_me folders as required
    #      Get info from file metadata (DONE)
    #      DONE: Should I do it for all files again and again or
    #      should I check for changes from last time?
    #    - update index.html DONE
    # 3. TODO: Handle additional files (like images and stuff for the generated html files)
    # NOTE: I think filter by single tag can be done statically,
    #       but filter by multiple tags has to be JS
    def sanity_check(self):
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        shutil.copytree(self.assets_dir,
                        os.path.join(self.output_dir, self.assets_dir.split("/")[-1]),
                        dirs_exist_ok=True)

    def extract_metadata(self, filename):
        with open(filename) as f:
            doc = yaml.load_all(f, Loader=yaml.FullLoader)
            yaml_metadata = doc.__next__()
        return yaml_metadata

    def check_for_changes(self, update_all=False):
        if os.path.exists(self.files_data) and not update_all:
            with open(self.files_data) as f:
                files_data = json.load(f)
        else:
            if update_all:
                print(f"Updating all files")
            files_data = {"files": {}}
        files = os.listdir(self.input_dir)
        for f in files:
            if f.endswith(".md"):
                if f not in files_data["files"]:
                    files_data["files"][f] = {}
                    with open(os.path.join(self.input_dir, f)) as _f:
                        hash = hashlib.md5(_f.read().encode("utf-8")).hexdigest()
                    files_data["files"][f]["hash"] = hash
                    files_data["files"][f]["metadata"] = self.extract_metadata(
                        os.path.join(self.input_dir, f))
                    metadata = files_data["files"][f]["metadata"]
                    if "ignore" in metadata and metadata["ignore"]:
                        print(f"Ingore set to true. Ignoring file {f}")
                        files_data["files"].pop(f)
                    else:
                        files_data["files"][f]["update"] = True
                else:
                    with open(os.path.join(self.input_dir, f)) as _f:
                        hash = hashlib.md5(_f.read().encode("utf-8")).hexdigest()
                    if not hash == files_data["files"][f]["hash"]:
                        files_data["files"][f]["hash"] = hash
                        files_data["files"][f]["metadata"] = self.extract_metadata(
                            os.path.join(self.input_dir, f))
                        metadata = files_data["files"][f]["metadata"]
                        if "ignore" in metadata and not metadata["ignore"]:
                            files_data["files"][f]["update"] = True
                        else:
                            files_data["files"].pop(f)
                            print(f"Ingore set to true. Ignoring file {f}")
                    else:
                        files_data["files"][f]["update"] = False
        with open(self.files_data, "w") as dump_file:
            json.dump(files_data, dump_file, default=str)
        self.files_data = files_data

    def generate_post_page(self, post_file, metadata):
        p = Popen(f"{self.post_cmd} {post_file}",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if err:
            print(err)
        page = out.decode("utf-8")
        date = metadata["date"]
        tags = metadata["tags"].split(",")
        tags = [t.strip().replace(" ", "_").lower() for t in tags]
        tags = ", ".join([f"<a href='../tags/{tag}.html'>{tag}</a>" for tag in tags])
        category = metadata["category"]
        edited = None
        if "edited" in metadata:
            edited = metadata["edited"]
        page = self.fix_title(category, page, prefix=True)
        page = page.replace("$ADD_DATA$", f'<span>Posted on: {date},' +
                            (f' Edited on: {edited},' if edited else '') + ' in Category:' +
                            f' <a href="../{category}.html">{category}</a>' +
                            (f", tags: {tags}" if tags else "") + "</span>")
        return page

    # TODO: code formatting for programming stuff
    def generate_posts(self):
        for fname, fval in self.files_data["files"].items():
            metadata = fval["metadata"]
            if "category" in metadata:  # only posts have categories
                out_file = os.path.join(self.output_dir, metadata["category"].lower(),
                                        fname.replace(".md", ".html"))
                if fval["update"] or not os.path.exists(out_file):
                    print(f"Generating post {fname}")
                    page = self.generate_post_page(os.path.join(self.input_dir, fname),
                                                   metadata)
                    with open(out_file, "w") as f:
                        f.write(page)

    def update_category_and_post_pages(self):
        categories = {}
        for fname, fval in self.files_data["files"].items():
            meta = fval["metadata"]
            # page without category is a root page
            if "category" in meta:
                if meta["category"] not in categories:
                    categories[meta["category"]] = []
                categories[meta["category"]].append(fname)
        self.categories = [*categories.keys()]
        for cat, pages in categories.items():
            if not os.path.exists(os.path.join(self.output_dir, cat)):
                os.mkdir(os.path.join(self.output_dir, cat))
            pages.sort(key=lambda x: self.files_data["files"][x]["metadata"]["date"])
        self.generate_posts()
        index_data = []
        for cat, pages in categories.items():
            # - filter by tags may only work with javascript
            # - page.insert snippet with a <next> for let's say 5-6 results per page
            # if noscript then show everything (no <next> tags)
            data = []
            for i, page in enumerate(pages):
                temp = {}
                temp["date"] = self.files_data["files"][page]["metadata"]["date"]
                tags = self.files_data["files"][page]["metadata"]["tags"]
                tags = [t.strip() for t in tags.split(",")]
                temp["tags"] = [t.replace(" ", "_").lower() for t in tags]
                html_file = os.path.join(self.output_dir, cat, page.replace(".md", ".html"))
                temp["snippet"] = self.get_snippet_content(html_file)
                temp["path"] = "/".join([cat, page.replace(".md", ".html")])
                data.append(temp)
                if not i:       # ignore heading
                    index_data.append({**temp, "category": cat})
            print(f"Generating category {cat} page")
            self.generate_category_page(cat, data)
        self.index_data = index_data

    def get_snippet_content(self, html_file):
        if html_file not in self._snippet_cache:
            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), features="lxml")
            heading = soup.find("title").text
            paras = soup.findAll("p")
            text = []
            while len(text) <= 70:
                para = paras.pop(0)
                text.extend(para.text.split(" "))
            self._snippet_cache[html_file] = SimpleNamespace(
                **{"heading": heading, "text": " ".join(text)})
        return self._snippet_cache[html_file]

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
        category = category.lower()
        if category in self.titles:
            if prefix:
                script_tag = f'<script type="text/javascript" ' +\
                    f'src="../assets/js/{category}_titles.js"></script>'
            else:
                script_tag = f'<script type="text/javascript" ' +\
                    f'src="assets/js/{category}_titles.js"></script>'
            page = page.replace("$TITLES_FILE$", script_tag)
            default_title = self.titles[category][0]
        else:
            print(f"Category {category} not in titles.json")
            page = page.replace("$TITLES_FILE$", "")
            default_title = self.titles["index"][0]
        page = re.sub('<p><h1 align="center">(.*)</h1></p>', '<h1 align="center">\\1</h1>', page)
        return re.sub('<h1 class="title">.*</h1>',
                      f'<h1 class="title">{default_title}</h1>', page)

    # TODO: I was thinking to use pypandoc, but that calls subprocess anyway
    #       instead of interfacing with haskell libs. Better to write my own
    #       input and output parser for pandoc, similar to pandocwatch
    def generate_index_page(self, data):
        print(f"Generating index page")
        p = Popen(f"{self.index_cmd} blog_input/index.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        index_path = os.path.join("blog_output", "index.html")
        snippets = []
        data.sort(key=lambda x: x["date"], reverse=True)
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = ", ".join([f"<a href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            category = d["category"]
            snippets.append(snippet_string_with_category(snippet, path, date, category, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        page = self.fix_title("index", page)
        with open(index_path, "w") as f:
            f.write(page)

    # TODO: JS 5-6 snippets at a time with <next> etc.
    def generate_category_page(self, category, data):
        p = Popen(f"{self.category_cmd} blog_input/{category}.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        snippets = []
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = ", ".join([f"<a href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            snippets.append(snippet_string(snippet, path, date, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        page = self.fix_title(category, page)
        with open(os.path.join(self.output_dir, f"{category}.html"), "w") as f:
            f.write(page)

    def generate_tag_pages(self):
        p = Popen(f"{self.tag_cmd} blog_input/tag.md",
                  shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories, "../")
        page = page.replace("$INDEX_TOC$", menu_string)
        page = page.replace("href=\"assets/", "href=\"../assets/")
        page = page.replace("src=\"assets/", "src=\"../assets/")
        all_tags = {}
        for fname, fval in self.files_data["files"].items():
            if "category" in fval["metadata"]:  # only posts
                tags = fval["metadata"]["tags"]
                tags = [t.strip().replace(" ", "_").lower() for t in tags.split(",")]
                for tag in tags:
                    if tag not in all_tags:
                        all_tags[tag] = []
                    all_tags[tag].append([fname, fval["metadata"]["category"],
                                          fval["metadata"]["date"]])
        if not os.path.exists(self.tag_pages_dir):
            os.mkdir(self.tag_pages_dir)
        for tag, files in all_tags.items():
            tag_page = page.replace("$TAG$", tag)
            snippets = []
            for fname, category, date in files:
                _fname = fname.replace(".md", ".html")
                snippet = self.get_snippet_content(os.path.join(
                    self.output_dir, category, fname.replace(".md", ".html")))
                path = f"../{category}/{_fname}"
                snippets.append(snippet_string_with_category(snippet, path, date, category,
                                                             cat_path_prefix="../"))
            tag_page = tag_page.replace("$SNIPPETS$", "\n".join(snippets))
            tag_page = self.fix_title("index", tag_page, True)
            with open(os.path.join(self.tag_pages_dir, f"{tag}.html"), "w") as f:
                f.write(tag_page)

    def generate_other_pages(self):
        self.generate_about_page()
        self.generate_links_page()
        self.generate_quotes_page()

    def generate_about_page(self):
        # has to have links to my githbut repo, linkedin profile, CV
        pass

    def generate_links_page(self):
        pass

    def generate_quotes_page(self):
        pass


# NOTE: Initialize and export the function
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--update-all", action="store_true",
                        help="Force update all files regardless of " +
                        "the fact if they've changed or not")
    # FIXME: Unused
    parser.add_argument("-c", "--config-file", default="",
                        help="Config file to use (dummy as of now)")
    parser.add_argument("-i", "--input-dir", default="input",
                        help="Input directory for the blog contents")
    parser.add_argument("-o", "--output-dir", default="output",
                        help="Where to output the blog contents")
    parser.add_argument("-l", "--layout-dir", default="layout",
                        help="Directory for the blog templates and layout")
    # FIXME: Unused
    parser.add_argument("-p", "--prompt", action="store_true",
                        help="Prompt from user before adding any new file")
    parser.add_argument("--csl-dir", default="csl",
                        help="Directory where the csl files are kept")
    parser.add_argument("--assets-dir", default="assets",
                        help="Location of assets dir containing js, css files etc.")
    parser.add_argument("--exclude-dirs",
                        default=",".join(["assets", "images", "documents", "tags"]),
                        help="Dirs to exclude from including in category pages")
    args = parser.parse_args()
    config = configparser.ConfigParser()
    # NOTE: Config file can contain pandoc generation options also
    if args.config_file and os.path.exists(args.config_file):
        config.read(args.config_file)
    elif os.path.exists("config.ini"):
        config.read("config.ini")
    else:
        print("No config file present. Using defaults")
    # HACK: Should override these from config
    input_dir = "blog_input"
    output_dir = "blog_output"
    layout_dir = "settings/blog"
    csl_dir = "settings/csl"
    assets_dir = "settings/blog/assets"
    # FIXME: This is unused
    exclude_dirs = args.exclude_dirs.split(",")
    post_processor = BlogGenerator(input_dir, output_dir, layout_dir, csl_dir,
                                   assets_dir, exclude_dirs)
    post_processor.run_pipeline(args.update_all)


if __name__ == "__main__":
    main()
