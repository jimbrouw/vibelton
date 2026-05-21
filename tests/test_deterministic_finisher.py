from __future__ import annotations

import unittest

from vibelton.planner import local_plan


class DeterministicFinisherTest(unittest.TestCase):
    def test_humanize_prompt_is_repeatable(self) -> None:
        first = local_plan("Humanize the drums and add ghost notes.")
        second = local_plan("Humanize the drums and add ghost notes.")
        self.assertEqual(first["actions"], second["actions"])

    def test_ghost_note_prompt_is_repeatable(self) -> None:
        first = local_plan("Add ghost notes to the drums.")
        second = local_plan("Add ghost notes to the drums.")
        self.assertEqual(first["actions"], second["actions"])


if __name__ == "__main__":
    unittest.main()
