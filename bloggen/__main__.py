import os
import argparse
import configparser


# NOTE: Initialize and export the function
def main():
    from .blog_generator import BlogGenerator
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--update-all", action="store_true",
                        help="Force update all files regardless of " +
                        "the fact if they've changed or not")
    # FIXME: Unused
    parser.add_argument("-c", "--config-file", default="",
                        help="Config file to use (dummy as of now)")
    parser.add_argument("-i", "--input-dir", default="input",
                        help="Input directory for the blog contents (default: input)")
    parser.add_argument("-o", "--output-dir", default="output",
                        help="Where to output the blog contents (default: output)")
    # FIXME: Unused
    parser.add_argument("-p", "--prompt", action="store_true",
                        help="Prompt from user before adding any new file")
    parser.add_argument("--csl-dir", default="csl",
                        help="Directory where the csl files are located (default: csl)")
    parser.add_argument("--assets-dir", default="assets",
                        help="Location of assets dir containing js, css files etc. (default: assets)")
    parser.add_argument("--templates-dir", default="templates",
                        help="Directory for of pandoc templates (default: templates)")
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
    # FIXME: This is unused
    exclude_dirs = args.exclude_dirs.split(",")
    generator = BlogGenerator(args.input_dir, args.output_dir, args.templates_dir,
                              args.csl_dir, args.assets_dir, exclude_dirs)
    generator.run_pipeline(args.update_all)


if __name__ == "__main__":
    main()
