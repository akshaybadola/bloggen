import os
from pathlib import Path
import argparse
import configparser
from types import SimpleNamespace
from common_pyutil.functional import first_by

from .util import print_
from .files import Files


def check_arguments(args: SimpleNamespace, config: configparser.ConfigParser,
                    parser: argparse.ArgumentParser):
    all_args = [*args.__dict__.keys(), "files_data_hash"]

    def check_bib_dirs(arg):
        arg = arg.split(",")
        if all(map(os.path.exists, arg)):
            return arg
        else:
            raise ValueError()

    def check_csl_file(arg):
        if Path(args.csl_dir).joinpath(arg + ".csl").exists():
            return arg
        else:
            raise FileNotFoundError(f"File {Path(args.csl_dir).joinpath(arg + '.csl')} not found")

    # def check_files_data_hash(arg):
    #     input_dir = Path(args.input_dir)
    #     return check_files_data(input_dir, input_dir.joinpath(".files_data"), arg)

    def check_vars_file(arg):
        return str(first_by([Path(arg),
                             Path(args.input_dir).joinpath(arg),
                             Path(args.input_dir).joinpath(Path(arg).name)],
                            Path.exists).absolute()
                   or "")

    arg_checks = SimpleNamespace(
        **{"bib_dirs": check_bib_dirs,
           "citation_style": check_csl_file,
           # "files_data_hash": check_files_data_hash,
           "variables": check_vars_file})
    for k in set([*args.__dict__.keys(), *config["default"].keys()]):
        if k not in all_args:
            raise AttributeError(f"Unknown Configuration Argument \"{k}\"")
    if config["default"]:
        print_("Checking config:")
    for x in config["default"]:
        func = getattr(arg_checks, x, None) or (lambda *x: True)
        if func:
            arg = func(config["default"][x])
        if not getattr(args, x, None) or (getattr(args, x) == parser.get_default(x)):
            print_(f"Setting \"{x}\" from config to \"{arg}\"", "\t")
            setattr(args, x, arg)
    for x in args.__dict__.keys():
        if x not in config["default"] and x in arg_checks.__dict__.keys():
            getattr(arg_checks, x)(getattr(args, x))
    print_("\n")


# NOTE: Initialize and export the function
def main():
    from .generator import BlogGenerator
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--update-all", action="store_true",
                        help="Force update all files regardless of " +
                        "the fact if they've changed or not")
    parser.add_argument("--dry-run", action="store_true",
                        help="Do not make any updates but only check input and output.")
    parser.add_argument("-c", "--config-file", default="",
                        help="Config file to use (dummy as of now)")
    parser.add_argument("-i", "--input-dir", default="input",
                        help="Input directory for the blog contents (default: input)")
    parser.add_argument("--input-pattern", type=str, default="",
                        help="Compile only files matching pattern")
    parser.add_argument("-o", "--output-dir", default="output",
                        help="Where to output the blog contents (default: output)")
    # FIXME: Unused
    parser.add_argument("--prompt", action="store_true",
                        help="Prompt from user before adding any new file")
    parser.add_argument("--csl-dir", default="csl",
                        help="Directory where the csl files are located (default: csl)")
    parser.add_argument("--themes-dir", default="themes",
                        help="Location of themes dir (default: themes)")
    parser.add_argument("-t", "--theme", default="default",
                        help="Name of the theme (default: default)")
    parser.add_argument("--bib-dirs", default=["bibs"],
                        help="Directories to search for bibtex files (default: [bibs])")
    parser.add_argument("--exclude-dirs",
                        default=",".join(["assets", "images", "documents", "tags"]),
                        help="Dirs to exclude from including in category pages")
    parser.add_argument("--citation-style",
                        default="ieee",
                        help="\n".join(["Which citations style to use.",
                                        "The value denotes the name of which CSL file to use.",
                                        "The CSL file must be present in the CSL directory."]))
    parser.add_argument("--variables", type=str, default="variables.json",
                        help="File containing variables like custom titles in JSON format")
    parser.add_argument("-p", "--preview", action="store_true",
                        help="Generate a blog preview regardless of changes")
    parser.add_argument("-u", "--update-styles", action="store_true",
                        help="Only update the styles, don't generate anything")
    args = parser.parse_args()
    config = configparser.ConfigParser(default_section="default")
    # NOTE: Config file can contain pandoc generation options also
    if args.config_file and os.path.exists(args.config_file):
        config.read(args.config_file)
    elif os.path.exists("config.ini"):
        args.config_file = Path("config.ini")
        config.read("config.ini")
    else:
        print_("No config file present. Using defaults")

    check_arguments(args, config, parser)
    print_("Checking files:")
    files = Files(Path(args.input_dir), Path(args.output_dir),
                  Path(args.input_dir).joinpath(".files_data"),
                  update_all=args.update_all)
    files.check_for_changes(include_drafts=args.preview,
                            input_pattern=args.input_pattern)
    if not files.changes:
        print_("No changes to files", "\t")
    if not any([files.changes, args.update_all, args.update_styles]):
        print_("Nothing to do", "\t")
        return 0
    print_("\n")
    # FIXME: This is unused
    exclude_dirs = args.exclude_dirs.split(",")
    params = map(Path, [args.input_dir, args.output_dir, args.themes_dir,
                        args.csl_dir, args.variables])
    if args.preview:
        out_dir = Path(args.output_dir).absolute().parent.joinpath("preview")
    else:
        if files.changes:
            files.write_files_data()
        out_dir = Path(args.output_dir)
    gen_files = files.generation_files(args.preview)
    if any([files.changes, args.update_all, args.update_styles]):
        generator = BlogGenerator(*params, args.theme, args.bib_dirs, exclude_dirs,
                                  args.citation_style, args.dry_run,
                                  contact={k: v for k, v in config["contact"].items()},
                                  pandoc_config={k: v for k, v in config["pandoc"].items()})
        if args.update_styles:
            if not out_dir.exists():
                print("Cannot update styles only in empty dir")
            else:
                generator.update_styles(out_dir)
        else:
            generator.run_pipeline(out_dir, gen_files,
                                   args.preview, args.update_all,
                                   args.input_pattern)


if __name__ == "__main__":
    main()
