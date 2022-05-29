import os
import tempfile


def slurp(filename):
    with open(filename) as file_:
        return file_.read()


def slurp_lines(filename):
    with open(filename) as file_:
        return [line.strip() for line in file_.readlines()]


def spit(filename, contents):
    with open(filename, 'w', encoding='utf-8') as file_:
        file_.write(contents)


def in_temp_dir(filename) -> str:
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, filename)
