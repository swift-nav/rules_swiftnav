#!/usr/bin/env python3

"""
Usages: stamp_file.py <status_file> <template_file> <output_file>
"""

import argparse


def init() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("status")
    parser.add_argument("template")
    parser.add_argument("output")
    return parser.parse_args()


def main() -> None:
    args = init()
    with open(args.status) as status, open(args.template) as tpl, open(
        args.output, "w"
    ) as out:
        template = tpl.read()
        for line in status.readlines():
            template = template.replace(
                "@" + line.split(" ", 1)[0] + "@", line.split(" ", 1)[1].strip()
            )

        out.write(template)


if __name__ == "__main__":
    main()
