#!/usr/bin/env python3

"""
Script for lulz.
"""

from string import Template

import argparse


def init() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("template")
    parser.add_argument("output")
    return parser.parse_args()


def main() -> None:
    args = init()
    with open(args.input) as input, open(args.template) as tpl, open(
        args.output, "w"
    ) as out:
        subs = dict(
            (line.split(" ")[0], line.split(" ")[1]) for line in input.readlines()
        )
        s = Template(tpl.read())
        out.write(s.substitute(subs))


if __name__ == "__main__":
    main()
