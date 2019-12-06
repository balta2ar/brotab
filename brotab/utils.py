import re

from base64 import urlsafe_b64decode, urlsafe_b64encode
from os.path import getsize


def split_tab_ids(string):
    items = re.split(r'[ \t\r\n]+', string)
    return list(filter(None, items))


def encode_query(string):
    return str(urlsafe_b64encode(string.encode('utf-8')), 'utf-8')


def decode_query(string):
    return urlsafe_b64decode(string).decode('utf-8')


def get_file_size(path):
    try:
        return getsize(path)
    except FileNotFoundError:
        return None
