import unittest

from problem_parsing_env.builder_core import build_spec
from problem_parsing_env.solver_core import solve


class DiscBrakeTests(unittest.TestCase):
    def test_disc_brake_uniform_wear(self):
        text = (
            "A disc brake has friction coefficient 0.32. The normal force pressing the pad is 14 kN. "
            "The inner radius of the contact annulus is 70 mm and the outer radius is 120 mm. "
            "Assuming uniform wear, compute the braking torque."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "clutch.single_disc.uniform_wear")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        self.assertIn("geometry", inputs)
        self.assertIn("loads", inputs)

        result = solve(spec)
        self.assertIn("T", result)
        self.assertGreater(result["T"], 0.0)

    def test_disc_brake_uniform_pressure(self):
        text = (
            "A single-disc clutch with friction coefficient 0.30 transmits a normal force of 10 kN. "
            "The contact surface has inner radius 60 mm and outer radius 110 mm. "
            "Assuming uniform pressure distribution, determine the torque capacity."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "clutch.single_disc.uniform_pressure")
        self.assertFalse(spec["ambiguities"])

        result = solve(spec)
        self.assertIn("T", result)
        self.assertGreater(result["T"], 0.0)


if __name__ == "__main__":
    unittest.main()
