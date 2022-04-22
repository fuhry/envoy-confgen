import sys
import argparse

from envoyconfgen.convert import do_translate
from envoyconfgen import processors

def main():
    ap = argparse.ArgumentParser()

    all_processors = list(processors.all())

    ap.add_argument('-o', '--output', action='store', required=False, help='Output file to write to - defaults to stdout')
    ap.add_argument(
        '-p', '--processor',
        action='store',
        help="Which processor to use to transform the input YAML",
        choices=[p.__name__ for p in all_processors],
        default=all_processors[0].__name__,
    )
    ap.add_argument('path', action='store', help='The listener map file to convert')
    args = ap.parse_args(sys.argv[1:])
    
    do_translate(args)

if __name__ == '__main__':
    main()
