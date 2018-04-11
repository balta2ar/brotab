from itertools import groupby

from brotab.tab import Tab
from brotab.tab import iter_window_tabs


# def _get_old_index(tab, tabs_before):
#     for index, value in enumerate(tabs_before):
#         if value == tab:
#             return index

#     raise ValueError('Tab %s not found' % tab)


# def _get_tab_id(tab):
#     index = tab.split('\t')[0]
#     str_index = index.split('.')[1]
#     return int(str_index)


def _get_index_by_tab_id(tab_id, tabs: [Tab]):
    for index, tab in enumerate(tabs):
        # if tab_id == _get_tab_id(tab):
        if tab_id == tab.tab_id:
            return index

    return None


def get_longest_increasing_subsequence(X):
    """Returns the Longest Increasing Subsequence in the Given List/Array"""
    N = len(X)
    P = [0] * N
    M = [0] * (N+1)
    L = 0
    for i in range(N):
       lo = 1
       hi = L
       while lo <= hi:
           mid = (lo+hi)//2
           if (X[M[mid]] < X[i]):
               lo = mid+1
           else:
               hi = mid-1

       newL = lo
       P[i] = M[newL-1]
       M[newL] = i

       if (newL > L):
           L = newL

    S = []
    k = M[L]
    for i in range(L-1, -1, -1):
        S.append(X[k])
        k = P[k]
    return S[::-1]


def infer_delete_commands(tabs_before: [Tab], tabs_after: [Tab]):

    # XXX: refactor this into a separate mapping class and use here and in
    # _get_old_index below
    tab_id_title_url_to_new_index = {
        (tab.tab_id, tab.title, tab.url): index
        for index, tab in enumerate(tabs_after)
    }

    commands = []
    after = set(tabs_after)
    for index in range(len(tabs_before) - 1, -1, -1):
        tab_before = tabs_before[index]

        key = (tab_before.tab_id, tab_before.title, tab_before.url)

        #if tab_before not in after:
        if key not in tab_id_title_url_to_new_index:
            # commands.append(_get_tab_id(tab_before))
            #commands.append(tab_before.tab_id)
            commands.append('%s.%s.%s' % (tab_before.prefix, tab_before.window_id, tab_before.tab_id))
    return commands


def _get_old_index(tab_after,
                   tab_line_to_old_index,
                   tab_id_title_url_to_old_index,
                   tabs_before):
    """
    Try to find out the index of the tab before the move.
    """
    # Easy case: tab has been just moved without changing window ID.
    if tab_after.line in tab_line_to_old_index:
        return tab_line_to_old_index[tab_after.line]

    # The tab might have window ID changed. Try to look for the title only.
    key = (tab_after.tab_id, tab_after.title, tab_after.url)
    if key in tab_id_title_url_to_old_index:
        return tab_id_title_url_to_old_index[key]

    # print('TAB AFTER', tab_after)
    # print('TAB AFTER LINE', tab_after.line)
    # print('KEY', key)
    #
    # from pprint import pprint
    # print('tab_line_to_old_index')
    # pprint(tab_line_to_old_index)
    #
    # print('tab_id_title_url_to_old_index')
    # pprint(tab_id_title_url_to_old_index)
    #
    # print('partilally matching keys in tab_line_to_old_index')
    # for line in tab_line_to_old_index:
    #     if tab_after.title in line:
    #         print('> %s' % line)

    # We're out of ideas...
    raise KeyError('Could not find line: "%s"' % tab_after.line)


def infer_move_commands(tabs_before: [Tab], tabs_after: [Tab]):
    """
    `tabs_before` and `tabs_after` contain an integer in the beginning
    but that's a tab ID, not a position. Thus, a move command means:

        move <tab_id> <to_index>

    where <to_index> is an index within a browser window. Consider this:

    Before:         After:
    f.4\ta          f.8\ta
    f.8\ta          f.4\ta
    f.1\aa          f.1\ta

    The correspoding move commands:

        move f.8 0

    """
    # Remember which tab corresponds to which index in the old list
    tab_line_to_old_index = {tab.line: index for index, tab in enumerate(tabs_before)}
    # XXX: use tab ID + title + URL as the key
    tab_id_title_url_to_old_index = {
        (tab.tab_id, tab.title, tab.url): index
        for index, tab in enumerate(tabs_before)
    }

    # Now see how indices have been reordered by user
    #reordered_indices = [tab_line_to_old_index[tab.line] for tab in tabs_after]
    reordered_indices = [_get_old_index(tab_after,
                                        tab_line_to_old_index,
                                        tab_id_title_url_to_old_index,
                                        tabs_before)
                         for tab_after in tabs_after]
    # These indices are in correct order, we should not touch them
    correctly_ordered_new_indices = set(
        get_longest_increasing_subsequence(reordered_indices))

    commands = []
    upward, downward = [], []

    #print('reordered_indices', reordered_indices)
    #print('tab_id_title_url_to_old_index', tab_id_title_url_to_old_index)

    for new_index, old_index in enumerate(reordered_indices):
        tab_before = tabs_before[old_index]
        tab_after = tabs_after[new_index]

        index_changed = old_index not in correctly_ordered_new_indices
        window_changed = tab_before.window_id != tab_after.window_id

        if index_changed or window_changed:
            triplet = (tab_before.tab_id, tab_after.window_id, new_index)
            upward.append(triplet) if new_index > old_index else downward.append(triplet)
    commands = downward + list(reversed(upward))
    return commands


def apply_delete_commands(tabs_before: [Tab], delete_commands):
    tabs = tabs_before[:]
    #for tab_id in delete_commands:
    for delete_command in delete_commands:
        prefix, window_id, tab_id = delete_command.split('.')
        window_id, tab_id = int(window_id), int(tab_id)
        #tab_id = int(command.split()[1])
        del tabs[_get_index_by_tab_id(tab_id, tabs)]
    return tabs


def apply_move_commands(tabs_before: [Tab], move_commands):
    tabs = tabs_before[:]
    for tab_id, window_id, index_to in move_commands:
        index_from = _get_index_by_tab_id(tab_id, tabs)
        tab = tabs.pop(index_from)
        # XXX: should we update the window_id?
        tab.window_id = window_id
        tabs.insert(index_to, tab)
    return tabs


def infer_delete_and_move_commands(tabs_before: [Tab], tabs_after: [Tab]):
    """
    This command takes browser tabs before the edit and after the edit and
    infers a sequence of commands that need to be executed in a browser
    to make transform state from `tabs_before` to `tabs_after`.

    Sample input:
        f.0.0	GMail
        f.0.1	Posix man
        f.0.2	news

    Sample output:
        m 0 5,m 1 1,d 2
    Means:
        move 0 to index 5,
        move 1 to index 1,
        delete 2

    Note that after moves and deletes, indices do not need to be adjusted on the
    browser side. All the indices are calculated by the client program so that
    the JS extension can simply execute the commands without thinking.
    """
    # For now, let's work only within chunks of tabs grouped by
    # the windowId, i.e. moves between windows of the same browser are not
    # supported yet.
    delete_commands, move_commands = [], []
    # for _window_id, chunk_before, chunk_after in iter_window_tabs(tabs_before, tabs_after):
    #     delete_commands.extend(infer_delete_commands(chunk_before, chunk_after))
    #     chunk_before = apply_delete_commands(chunk_before, delete_commands)
    #     move_commands.extend(infer_move_commands(chunk_before, chunk_after))

    # I've added moves across different exisitng (!) windows of the same
    # browser to iter_window_tabs is not used.

    # [_] detect a move to a new nonexisting window

    delete_commands.extend(infer_delete_commands(tabs_before, tabs_after))
    # print('DELETE', delete_commands)
    tabs_before = apply_delete_commands(tabs_before, delete_commands)
    move_commands.extend(infer_move_commands(tabs_before, tabs_after))

    return delete_commands, move_commands
