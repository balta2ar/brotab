from unittest import TestCase

from brotab_client import infer_delete_and_move_commands


class TestInferDeleteMoveCommands(TestCase):
    def _eq(self, tabs_before, tabs_after, expected_commands):
        actual_commands = infer_delete_and_move_commands(tabs_before, tabs_after)
        self.assertEqual(expected_commands, actual_commands)

    def test_only_deletes(self):
        self._eq(
            ['f.0.0	First',
             'f.0.1	Second',
             'f.0.2	Third'],
            ['f.0.2	Third'],
            ['delete 1', 'delete 0']
        )

        self._eq(
            ['f.0.0	First',
             'f.0.1	Second',
             'f.0.2	Third',
             'f.0.3	Fourth'],
            ['f.0.0	First', 'f.0.2	Third'],
            ['delete 3', 'delete 1']
        )

    def test_only_moves(self):
        self._eq(
            [
                'f.0.0	First',
                'f.0.1	Second',
                'f.0.2	Third'
            ],
            [
                'f.0.2	Third'
                'f.0.1	Second',
                'f.0.0	First',
            ],
            [
                'move 0 2',
            ]
        )

