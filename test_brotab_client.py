"""
Run:

    python3 -m unittest test_brotab_client

"""
from unittest import TestCase

from brotab_client import infer_delete_and_move_commands
# from brotab_client import get_longest_contiguous_increasing_sequence
from brotab_client import get_longest_increasing_subsequence
from brotab_client import infer_move_commands
from brotab_client import apply_move_commands


# class TestLIS(TestCase):
#     def test_one(self):
#         seq = [1, 3, 0, 5, 6, 4, 7, 2, 0]
#         result = get_longest_increasing_subsequence(seq)
#         self.assertEqual([1, 3, 5, 6, 7], result)


class TestReconstruct(TestCase):
    def test_one_move_from_start_to_end(self):
        before = [
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
        ]
        after = [
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
            'f.0\ta',
        ]
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(0, 4)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_one_move_from_end_to_start(self):
        before = [
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
        ]
        after = [
            'f.4\ta',
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
        ]
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(4, 0)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_one_move_from_start_to_center(self):
        before = [
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
            'f.5\ta',
            'f.6\ta',
            'f.7\ta',
            'f.8\ta',
        ]
        after = [
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
            'f.0\ta',
            'f.5\ta',
            'f.6\ta',
            'f.7\ta',
            'f.8\ta',
        ]
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(0, 4)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)

    def test_crossings(self):
        before = [
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.4\ta',
            'f.5\ta',
            'f.6\ta',
            'f.7\ta',
            'f.8\ta',
        ]
        after = [
            'f.4\ta',
            'f.0\ta',
            'f.1\ta',
            'f.2\ta',
            'f.3\ta',
            'f.6\ta',
            'f.7\ta',
            'f.8\ta',
            'f.5\ta',
        ]
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(4, 0), (5, 8)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)


    def test_decreasing_ids_from_start_to_end(self):
        before = [
            'f.10\ta',
            'f.9\ta',
            'f.8\ta',
            'f.7\ta',
        ]
        after = [
            'f.9\ta',
            'f.8\ta',
            'f.7\ta',
            'f.10\ta',
        ]
        commands = infer_move_commands(before, after)
        self.assertEqual(commands, [(10, 3)])
        actual_after = apply_move_commands(before, commands)
        self.assertEqual(actual_after, after)


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


class TestInferDeleteMoveCommands(TestCase):
    def _eq(self, tabs_before, tabs_after, expected_deletes, expected_moves):
        deletes, moves = infer_delete_and_move_commands(tabs_before, tabs_after)
        self.assertEqual(expected_deletes, deletes)
        self.assertEqual(expected_moves, moves)

    def test_only_deletes(self):
        self._eq(
            ['f.0	First',
             'f.1	Second',
             'f.2	Third'],
            ['f.2	Third'],
            [1, 0],
            []
        )

        self._eq(
            ['f.0	First',
             'f.1	Second',
             'f.2	Third',
             'f.3	Fourth'],
            ['f.0	First', 'f.2	Third'],
            [3, 1],
            []
        )

    def test_only_moves(self):
        self._eq(
            [
                'f.0	First',
                'f.1	Second',
                'f.2	Third',
            ],
            [
                'f.2	Third',
                'f.0	First',
                'f.1	Second',
            ],
            [],
            [(2, 0)]
        )

        self._eq(
            [
                'f.0	First',
                'f.1	Second',
                'f.2	Third',
            ],
            [
                'f.2	Third',
                'f.1	Second',
                'f.0	First',
            ],
            [],
            [(2, 0), (1, 1)]
        )
