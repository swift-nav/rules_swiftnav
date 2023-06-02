"""
Usages: stamp_file.py <status_file> <defaults> <template_file> <output_file>
"""

import argparse, json, io


def init() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("status")
    parser.add_argument("defaults")
    parser.add_argument("template")
    parser.add_argument("output")
    return parser.parse_args()


def merge(status: io.TextIOWrapper, defaults: dict) -> dict:
    for line in status.readlines():
        defaults[line.split(" ", 1)[0]] = line.split(" ", 1)[1].strip()

    return defaults


def main() -> None:
    args = init()
    defaults = json.loads(args.defaults)

    with open(args.status) as status, open(args.template) as tpl, open(
        args.output, "w"
    ) as out:
        template = tpl.read()
        for key, val in merge(status, defaults).items():
            template = template.replace("@" + key + "@", val)

        out.write(template)


if __name__ == "__main__":
    main()
