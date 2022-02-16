#!python3

import sys

import init_scripts  # pylint: disable=unused-import

from app.helpers.utils import gzip_string


def main():
    if len(sys.argv) < 2:
        print('File argument missing')
        sys.exit(-1)

    file = sys.argv[1]
    with open(file, mode='r', encoding='utf-8') as fd:
        data = fd.read()

    gz_data = gzip_string(data)

    with open(file + '.gz', 'wb') as fd:
        fd.write(gz_data)


if __name__ == '__main__':
    main()
