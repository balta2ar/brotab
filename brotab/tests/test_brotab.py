from unittest import TestCase

from brotab.operations import apply_move_commands
from brotab.operations import apply_update_commands
from brotab.operations import infer_all_commands
from brotab.operations import infer_move_commands
from brotab.tab import parse_tab_lines


# class TestLIS(TestCase):
#     def test_one(self):
#         seq = [1, 3, 0, 5, 6, 4, 7, 2, 0]
#         result = get_longest_increasing_subsequence(seq)
#         self.assertEqual([1, 3, 5, 6, 7], result)


class TestReconstruct(TestCase):
    def test_move_one_from_start_to_end(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(0, 0, 4)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_one_from_end_to_start(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(4, 0, 0)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_one_from_start_to_center(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
            'f.0.7\ta\turl',
            'f.0.8\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
            'f.0.7\ta\turl',
            'f.0.8\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(0, 0, 4)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_crossings(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
            'f.0.7\ta\turl',
            'f.0.8\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.6\ta\turl',
            'f.0.7\ta\turl',
            'f.0.8\ta\turl',
            'f.0.5\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(4, 0, 0), (5, 0, 8)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_decreasing_ids_from_start_to_end(self):
        before = parse_tab_lines([
            'f.0.10\ta\turl',
            'f.0.9\ta\turl',
            'f.0.8\ta\turl',
            'f.0.7\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.9\ta\turl',
            'f.0.8\ta\turl',
            'f.0.7\ta\turl',
            'f.0.10\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(10, 0, 3)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_pair_from_start_to_end(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(1, 0, 4), (0, 0, 3)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_pair_from_end_to_start(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        # self.assertEqual(commands, [(1, 0, 4), (0, 0, 3)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_several_upwards(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.1\ta\turl',
            'f.0.3\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
            'f.0.0\ta\turl',
            'f.0.2\ta\turl',
            'f.0.4\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        # self.assertEqual(commands, [(1, 0, 4), (0, 0, 3)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_several_downwards(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.2\ta\turl',
            'f.0.3\ta\turl',
            'f.0.4\ta\turl',
            'f.0.5\ta\turl',
            'f.0.6\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.2\ta\turl',
            'f.0.4\ta\turl',
            'f.0.6\ta\turl',
            'f.0.0\ta\turl',
            'f.0.1\ta\turl',
            'f.0.3\ta\turl',
            'f.0.5\ta\turl',
        ])
        commands = infer_move_commands(before, after)
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_move_one_to_another_existing_window_same_index(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
            'f.1.1\ta\turl',
        ])
        after = parse_tab_lines([
            'f.1.0\ta\turl',
            'f.1.1\ta\turl',
        ])
        delete_commands, move_commands, update_commands = infer_all_commands(before, after)
        self.assertGreater(len(move_commands), 0)
        actual_after = apply_move_commands(before, move_commands)
        self.assertEqual(actual_after, after)

    def test_move_one_to_another_existing_window_below(self):
        before = parse_tab_lines([
            'f.0.0\ta1\turl1',
            'f.1.1\ta2\turl2',
            'f.1.2\ta3\turl3',
        ])
        after = parse_tab_lines([
            'f.1.1\ta2\turl2',
            'f.1.2\ta3\turl3',
            'f.1.0\ta1\turl1',
        ])
        delete_commands, move_commands, update_commands = infer_all_commands(before, after)
        self.assertGreater(len(move_commands), 0)
        actual_after = apply_move_commands(before, move_commands)
        self.assertEqual(actual_after, after)

    def test_move_one_to_another_existing_window_above(self):
        before = parse_tab_lines([
            'f.0.0\ta1\turl1',
            'f.1.1\ta2\turl2',
            'f.1.2\ta3\turl3',
        ])
        after = parse_tab_lines([
            'f.0.2\ta3\turl3',
            'f.0.0\ta1\turl1',
            'f.1.1\ta2\turl2',
        ])
        delete_commands, move_commands, update_commands = infer_all_commands(before, after)
        self.assertGreater(len(move_commands), 0)
        actual_after = apply_move_commands(before, move_commands)
        self.assertEqual(actual_after, after)

    def test_move_one_to_another_existing_window_above_2(self):
        before = parse_tab_lines([
            'f.0.0\ta1\turl1',
            'f.0.1\ta2\turl2',
            'f.1.2\ta3\turl3',
            'f.1.3\ta4\turl4',
        ])
        after = parse_tab_lines([
            'f.0.0\ta1\turl1',
            'f.0.1\ta2\turl2',
            'f.0.3\ta4\turl4',
            'f.1.2\ta3\turl3',
        ])
        delete_commands, move_commands, update_commands = infer_all_commands(before, after)
        self.assertGreater(len(move_commands), 0)
        actual_after = apply_move_commands(before, move_commands)
        self.assertEqual(actual_after, after)

    def test_move_one_to_another_existing_window_several_mix(self):
        before = parse_tab_lines([
            'f.0.0\ta1\turl1',
            'f.0.1\ta2\turl2',
            'f.0.2\ta3\turl3',
            'f.1.3\ta3\turl4',
            'f.1.4\ta3\turl5',
            'f.1.5\ta3\turl6',
        ])
        after = parse_tab_lines([
            'f.0.5\ta3\turl6',
            'f.0.2\ta3\turl3',
            'f.1.3\ta3\turl4',
            'f.1.4\ta3\turl5',
            'f.1.0\ta1\turl1',
            'f.1.1\ta2\turl2',
        ])
        delete_commands, move_commands, update_commands = infer_all_commands(before, after)
        self.assertGreater(len(move_commands), 0)
        actual_after = apply_move_commands(before, move_commands)
        self.assertEqual(actual_after, after)

    # def test_move_one_to_another_existing_window_fixture_test1(self):
    #     before = parse_tab_lines(slurp_lines('tests/fixtures/move_to_another_window_test1_before.txt'))
    #     after = parse_tab_lines(slurp_lines('tests/fixtures/move_to_another_window_test1_after.txt'))
    #     delete_commands, move_commands = infer_delete_and_move_commands(before, after)
    #     print('COMMANDS', move_commands)
    #     self.assertGreater(len(move_commands), 0)
    #     actual_after = apply_move_commands(before, move_commands)
    #     self.assertEqual(actual_after, after)


# class TestSequence(TestCase):
#     def test_get_longest_contiguous_increasing_sequence(self):
#         tabs = [
#             'f.0\tFirst',
#             'f.1\tSecond',
#             'f.2\tThird',
#         ]
#         result = get_longest_contiguous_increasing_sequence(tabs)
#         self.assertEqual(result, (0, 3))

#         tabs = [
#             'f.4\te',
#             'f.1\tb',
#             'f.2\tc',
#             'f.3\td',
#             'f.0\ta',
#         ]
#         result = get_longest_contiguous_increasing_sequence(tabs)
#         self.assertEqual(result, (1, 3))

#         tabs = [
#             'f.4\te',
#             'f.1\tb',
#             'f.2\tc',
#             'f.3\td',
#             'f.0\ta',
#             'f.9\ta',
#             'f.5\tz',
#             'f.6\tz',
#             'f.7\tz',
#             'f.8\tz',
#         ]
#         result = get_longest_contiguous_increasing_sequence(tabs)
#         self.assertEqual(result, (6, 4))

#         tabs = [
#             'f.9\te',
#             'f.4\tz',
#             'f.5\tz',
#             'f.6\tz',
#             'f.7\tz',
#             'f.1\tb',
#             'f.2\tc',
#             'f.3\td',
#             'f.0\ta',
#         ]
#         result = get_longest_contiguous_increasing_sequence(tabs)
#         self.assertEqual(result, (1, 4))


class TestInferDeleteMoveUpdateCommands(TestCase):
    def _eq(self, tabs_before, tabs_after, expected_deletes, expected_moves, expected_updates):
        deletes, moves, updates = infer_all_commands(
            parse_tab_lines(tabs_before),
            parse_tab_lines(tabs_after))
        self.assertEqual(expected_deletes, deletes)
        self.assertEqual(expected_moves, moves)
        self.assertEqual(expected_updates, updates)

    def test_only_deletes(self):
        self._eq(
            ['f.0.0\ttitle\turl',
             'f.0.1\ttitle\turl',
             'f.0.2\ttitle\turl'],
            ['f.0.2\ttitle\turl'],
            ['f.0.1', 'f.0.0'],
            [],
            []
        )

        self._eq(
            ['f.0.0\ttitle\turl',
             'f.0.1\ttitle\turl',
             'f.0.2\ttitle\turl',
             'f.0.3\ttitle\turl'],
            ['f.0.0\ttitle\turl',
             'f.0.2\ttitle\turl'],
            ['f.0.3', 'f.0.1'],
            [],
            []
        )

    def test_only_moves(self):
        self._eq(
            [
                'f.0.0\ttitle\turl',
                'f.0.1\ttitle\turl',
                'f.0.2\ttitle\turl',
            ],
            [
                'f.0.2\ttitle\turl',
                'f.0.0\ttitle\turl',
                'f.0.1\ttitle\turl',
            ],
            [],
            [(2, 0, 0)],
            []
        )

        self._eq(
            [
                'f.0.0\ttitle\turl',
                'f.0.1\ttitle\turl',
                'f.0.2\ttitle\turl',
            ],
            [
                'f.0.2\ttitle\turl',
                'f.0.1\ttitle\turl',
                'f.0.0\ttitle\turl',
            ],
            [],
            [(2, 0, 0), (1, 0, 1)],
            []
        )


class TestUpdate(TestCase):
    def test_update_only_url(self):
        before = parse_tab_lines([
            'f.0.0\ta\turl',
        ])
        after = parse_tab_lines([
            'f.0.0\ta\turl_changed',
        ])
        deletes, moves, updates = infer_all_commands(before, after)
        self.assertEqual([], deletes)
        self.assertEqual([], moves)

        actual_after = apply_update_commands(before, updates)
        self.assertEqual(actual_after, after)
