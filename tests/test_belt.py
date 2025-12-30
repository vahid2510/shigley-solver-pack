import unittest

from problem_parsing_env.builder_core import build_spec
from problem_parsing_env.solver_core import solve


class BeltSolverTests(unittest.TestCase):
    def test_flat_belt_power(self):
        text = (
            "A flat belt drive transmits power between two pulleys. "
            "The tight-side tension is 1.6 kN while the slack-side tension is 0.6 kN. "
            "If the belt speed is 12 m/s, determine the power transmitted."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "belt.flat.power")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        self.assertIn("loads", inputs)
        self.assertIn("operating", inputs)

        result = solve(spec)
        self.assertIn("P", result)
        self.assertAlmostEqual(result["P"], (1600.0 - 600.0) * 12.0, places=6)

    def test_flat_belt_tension_ratio(self):
        text = (
            "A flat belt wraps around a pulley through an angle of contact of 170 degrees. "
            "The coefficient of friction between belt and pulley is 0.35. "
            "Compute the ratio of tight-side to slack-side tension."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "belt.flat.tension_ratio")
        self.assertFalse(spec["ambiguities"])

        result = solve(spec)
        self.assertIn("T1_over_T2", result)
        self.assertGreater(result["T1_over_T2"], 1.0)


if __name__ == "__main__":
    unittest.main()
