class Tab:
    def __init__(self, prefix, window_id, tab_id, title, url):
        self.prefix = prefix
        self.window_id = window_id
        self.tab_id = tab_id
        self.title = title
        self.url = url

    @property
    def id(self):
        return '{prefix}.{window_id}.{tab_id}'.format(
            prefix=self.prefix,
            window_id=self.window_id,
            tab_id=self.tab_id,
        )

    @property
    def line(self):
        return '{prefix}.{window_id}.{tab_id}\t{title}\t{url}'.format(
            prefix=self.prefix,
            window_id=self.window_id,
            tab_id=self.tab_id,
            title=self.title,
            url=self.url
        )

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(self.line)

    def __repr__(self):
        return self.line

    @staticmethod
    def from_line(line):
        ids, title, url = line.split('\t')
        prefix, window_id, tab_id = ids.split('.')
        return Tab(prefix, int(window_id), int(tab_id), title, url)


def parse_tab_lines(tab_lines):
    return [Tab.from_line(line) for line in tab_lines]


def iter_window_tabs(left: [Tab], right: [Tab]):
    # get_window_id = attrgetter('window_id')
    # left = sorted(left, key=get_window_id)
    # right = sorted(right, key=get_window_id)
    # groupby(left, get_window_id)

    all_window_ids = set(tab.window_id for tab in left + right)
    for window_id in all_window_ids:
        matching_left = list(filter(lambda x: x.window_id == window_id, left))
        matching_right = list(filter(lambda x: x.window_id == window_id, right))
        yield window_id, matching_left, matching_right
