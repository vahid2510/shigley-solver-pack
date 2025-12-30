import math
import unittest

from problem_parsing_env.builder_core import build_spec
from problem_parsing_env.solver_core import solve


class PowerScrewTests(unittest.TestCase):
    def test_power_screw_parsing_and_solver(self):
        text = (
            "A square-thread power screw is used to lift a load of 25 kN. "
            "The screw has a mean diameter of 36 mm with a single-start lead of 6 mm. "
            "Thread friction coefficient is 0.15. The bronze collar has mean diameter 60 mm "
            "with collar friction coefficient 0.08. Determine the torque required to raise the load."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "power.screw.raise")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        self.assertIn("geometry", inputs)
        self.assertIn("tribology", inputs)
        self.assertIn("loads", inputs)

        result = solve(spec)
        self.assertIn("T_total_raise", result)
        self.assertIn("efficiency", result)
        self.assertTrue(result["T_total_raise"] > 0.0)
        self.assertTrue(0.0 < result["efficiency"] < 1.0)

        # Independent check for torque using classical equations
        F = 25_000.0
        d_m = 0.036
        lead = 0.006
        mu = 0.15
        mu_c = 0.08
        d_c = 0.06

        alpha = math.atan(lead / (math.pi * d_m))
        phi = math.atan(mu)
        T_thread = F * d_m / 2.0 * math.tan(alpha + phi)
        T_collar = F * mu_c * d_c / 2.0
        expected_total = T_thread + T_collar
        self.assertTrue(math.isclose(result["T_total_raise"], expected_total, rel_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
