import sys
import argparse

from envoyzkfp.convert import do_translate

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument('path', action='store', help='The listener map file to convert')
    ap.add_argument('-o', '--output', action='store', required=False, help='Output file to write to - defaults to stdout')
    args = ap.parse_args(sys.argv[1:])

    do_translate(args)

if __name__ == '__main__':
    main()
