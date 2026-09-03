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
    def window(self):
        return '{prefix}.{window_id}'.format(
            prefix=self.prefix,
            window_id=self.window_id,
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


def get_per_window_indices(tabs):
    """Create a dict mapping each tab to its index within its window.

    This differs from the KeyToIndexMapper family of maps since those
    deal only in global positions.

    Args:
        tab_lines(list[str]): The list of tabs detailing window ID, tab
            ID, and title.

    Returns:
        dict[str, int]: A map from tab ID to per-window index.
    """
    window_index_counter = {}
    indices = {}
    for tab in tabs:
        index = window_index_counter.setdefault(tab.window, 0)
        indices[tab.tab_id] = index
        window_index_counter[tab.window] += 1

    return indices


def parse_groups(tab_lines):
    """Converts an array of flat {window_id}.{tab_id} lines into a
    grouped format. Each section describes the tabs of a certain
    window, starting with a line "Window {window_id}", followed by
    indented lines of the form "{tab_id} {title} {url}".

    This enables easier editing: tabs can still be deleted and moved
    around a window as in the classic editing style, but moving tabs
    from window to window is now simpler (the tab line can just be cut
    and pasted under a different Window heading; see
    `flatten_groups()` for more details).
    """
    tabs = parse_tab_lines(tab_lines)

    groups = {}
    for tab in tabs:
        win = groups.setdefault(tab.window, [])
        win.append(tab)

    lines = []
    for win, wintabs in groups.items():
        lines.append('Window {win}'.format(win=win))
        for tab in wintabs:
            tabline = '    {tab_id}\t{title}\t{url}'.format(
                tab_id=tab.tab_id,
                title=tab.title,
                url=tab.url,
            )
            lines.append(tabline)
        lines.append('')

    # Just omit that very last blank line.
    return lines[:-1]


def flatten_groups(lines):
    """Converts a list of parsed group tab lines back into the flat
    form. Essentially, this undoes the action of `parse_groups()`
    above.

    This is needed to convert an edited groupwise tab lines file back
    into the flat format the core logic of this program understands.
    """
    lines_out = []
    win = None
    for line in lines:
        if line == '':
            continue
        elif line.startswith('Window '):
            win = line.split(' ')[1]
        else:
            tab_parts = line.split('\t')
            tab_id = win + '.' + tab_parts[0]
            lines_out.append('\t'.join([tab_id] + tab_parts[1:]))

    return lines_out


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
