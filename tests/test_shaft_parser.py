import math
import unittest

from problem_parsing_env.builder_core import build_spec
from problem_parsing_env.solver_core import solve


class ShaftParserTests(unittest.TestCase):
    def assert_segment(self, segment, length, d_o, d_i=0.0, tol=1e-6):
        self.assertTrue(
            math.isclose(segment["length"], length, rel_tol=0, abs_tol=tol),
            msg=f"length {segment['length']} != {length}",
        )
        self.assertTrue(
            math.isclose(segment["d_o"], d_o, rel_tol=0, abs_tol=tol),
            msg=f"d_o {segment['d_o']} != {d_o}",
        )
        self.assertTrue(
            math.isclose(segment.get("d_i", 0.0), d_i, rel_tol=0, abs_tol=tol),
            msg=f"d_i {segment.get('d_i', 0.0)} != {d_i}",
        )

    def test_segmented_shaft_with_letters(self):
        text = (
            "A stepped steel shaft ABCD has segment AB 0.30 m long with 50 mm diameter, "
            "segment BC 0.20 m long with 40 mm diameter, and segment CD 0.15 m long with 35 mm diameter. "
            "The shaft is supported in bearings at A and D. "
            "A gear at B transmits a 4.5 kN tangential load and 1.2 kN radial load with pitch radius 75 mm. "
            "A 1.8 kN downward force acts at point C. Apply a torque of 120 N*m at D."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "shaft.analysis.segmented")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        segments = inputs["segments"]
        self.assertEqual(len(segments), 3)
        self.assert_segment(segments[0], 0.3, 0.05)
        self.assert_segment(segments[1], 0.2, 0.04)
        self.assert_segment(segments[2], 0.15, 0.035)

        supports = inputs["supports"]
        self.assertEqual({round(s["x"], 6) for s in supports}, {0.0, 0.65})

        loads = inputs["loads"]
        gear = next(ld for ld in loads if ld["type"] == "gear")
        self.assertTrue(math.isclose(gear["x"], 0.3, abs_tol=1e-6))
        self.assertTrue(math.isclose(gear["F_t"], 4500.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_r"], 1200.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["r"], 0.075, rel_tol=1e-9))

        point = next(ld for ld in loads if ld["type"] == "point_force")
        self.assertTrue(math.isclose(point["x"], 0.5, abs_tol=1e-6))
        self.assertTrue(math.isclose(point["Fz"], -1800.0, rel_tol=1e-9))

        torque = next(ld for ld in loads if ld["type"] == "torque")
        self.assertTrue(math.isclose(torque["x"], 0.65, abs_tol=1e-6))
        self.assertTrue(math.isclose(torque["T"], 120.0, rel_tol=1e-9))

        # Solver should consume the spec without raising
        result = solve(spec)
        self.assertIn("max_von_mises", result)

    def test_uniform_shaft_with_distributed_load(self):
        text = (
            "A steel drive shaft is 1.0 m long with diameter 45 mm throughout and is supported by bearings at each end. "
            "A gear located 0.25 m from the left bearing transmits a tangential load of 2.4 kN and a radial load of 1.1 kN "
            "with pitch diameter 200 mm. A uniformly distributed downward load of 0.6 kN/m acts between 0.4 m and 0.7 m. "
            "Apply a torque of 90 N*m at the right end."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "shaft.analysis.segmented")
        # Auto end-support assumption is acceptable; make sure that is the only ambiguity.
        self.assertEqual(len(spec["ambiguities"]), 1)
        self.assertIn("Assuming supports at shaft ends", spec["ambiguities"][0]["reason"])

        inputs = spec["inputs"]
        self.assertEqual(len(inputs["segments"]), 1)
        self.assert_segment(inputs["segments"][0], 1.0, 0.045)

        supports = sorted(inputs["supports"], key=lambda s: s["x"])
        self.assertTrue(math.isclose(supports[0]["x"], 0.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(supports[1]["x"], 1.0, abs_tol=1e-9))

        gear = next(ld for ld in inputs["loads"] if ld["type"] == "gear")
        self.assertTrue(math.isclose(gear["x"], 0.25, abs_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_t"], 2400.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_r"], 1100.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["r"], 0.1, rel_tol=1e-9))

        distributed = next(ld for ld in inputs["loads"] if ld["type"] == "distributed")
        self.assertTrue(math.isclose(distributed["start"], 0.4, abs_tol=1e-9))
        self.assertTrue(math.isclose(distributed["end"], 0.7, abs_tol=1e-9))
        self.assertIn("q_z", distributed)
        self.assertTrue(math.isclose(distributed["q_z"], -600.0, rel_tol=1e-9))

        torque = next(ld for ld in inputs["loads"] if ld["type"] == "torque")
        self.assertTrue(math.isclose(torque["x"], 1.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(torque["T"], 90.0, rel_tol=1e-9))

        result = solve(spec)
        self.assertIn("reactions", result)

    def test_mixed_unit_shaft(self):
        text = (
            "Consider shaft ABCD where segment AB 12 in long with 2.0 in diameter, "
            "segment BC 0.35 m long with 45 mm diameter, and segment CD 100 mm long with 30 mm diameter. "
            "Bearings support the shaft at A and D. "
            "At point C a gear transmits 1.8 kN tangential and 0.9 kN radial load with pitch radius 90 mm. "
            "A downward force of 350 lbf acts at point B. Apply a torque of 250 lb*ft at D."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "shaft.analysis.segmented")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        segments = inputs["segments"]
        self.assertEqual(len(segments), 3)
        self.assert_segment(segments[0], 0.3048, 0.0508)  # 12 in, 2 in
        self.assert_segment(segments[1], 0.35, 0.045)
        self.assert_segment(segments[2], 0.1, 0.03)

        supports = sorted(inputs["supports"], key=lambda s: s["x"])
        self.assertTrue(math.isclose(supports[0]["x"], 0.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(supports[-1]["x"], sum(seg["length"] for seg in segments), abs_tol=1e-6))

        gear = next(ld for ld in inputs["loads"] if ld["type"] == "gear")
        self.assertTrue(math.isclose(gear["x"], segments[0]["length"] + segments[1]["length"], abs_tol=1e-6))
        self.assertTrue(math.isclose(gear["F_t"], 1800.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_r"], 900.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["r"], 0.09, rel_tol=1e-9))

        point = next(ld for ld in inputs["loads"] if ld["type"] == "point_force")
        self.assertTrue(math.isclose(point["x"], segments[0]["length"], abs_tol=1e-6))
        self.assertTrue(math.isclose(point["Fz"], -350 * 4.4482216152605, rel_tol=1e-9))

        torque = next(ld for ld in inputs["loads"] if ld["type"] == "torque")
        self.assertTrue(math.isclose(torque["T"], 250 * 1.3558179483314004, rel_tol=1e-9))

        result = solve(spec)
        self.assertGreater(result["max_von_mises"]["value"], 0.0)

    def test_multiple_gears_with_offset_distances(self):
        text = (
            "A stepped shaft ABCD has segment AB 0.25 m long with 50 mm diameter, "
            "segment BC 0.15 m long with 42 mm diameter, and segment CD 0.20 m long with 38 mm diameter. "
            "Bearings support the shaft at A and D. "
            "A gear at B transmits 3.2 kN tangential and 1.0 kN radial load with pitch radius 60 mm. "
            "Another gear located 0.10 m from point C toward the right transmits 2.4 kN tangential and 0.8 kN radial load "
            "with pitch radius 40 mm. Apply a torque of 150 N*m at D."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "shaft.analysis.segmented")
        self.assertFalse(spec["ambiguities"])

        inputs = spec["inputs"]
        segments = inputs["segments"]
        self.assertEqual(len(segments), 3)
        total_length = sum(seg["length"] for seg in segments)
        self.assertTrue(math.isclose(total_length, 0.6, abs_tol=1e-9))

        gears = [ld for ld in inputs["loads"] if ld["type"] == "gear"]
        self.assertEqual(len(gears), 2)
        gears_sorted = sorted(gears, key=lambda g: g["x"])

        self.assertTrue(math.isclose(gears_sorted[0]["x"], segments[0]["length"], abs_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[0]["F_t"], 3200.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[0]["F_r"], 1000.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[0]["r"], 0.06, rel_tol=1e-9))

        expected_second_x = segments[0]["length"] + segments[1]["length"] + 0.10
        self.assertTrue(math.isclose(gears_sorted[1]["x"], expected_second_x, abs_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[1]["F_t"], 2400.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[1]["F_r"], 800.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gears_sorted[1]["r"], 0.04, rel_tol=1e-9))

        torque = next(ld for ld in inputs["loads"] if ld["type"] == "torque")
        self.assertTrue(math.isclose(torque["x"], total_length, abs_tol=1e-9))
        self.assertTrue(math.isclose(torque["T"], 150.0, rel_tol=1e-9))

    def test_gear_position_from_right_end_reference(self):
        text = (
            "A uniform steel shaft of length 0.9 m and diameter 32 mm is supported by bearings at its ends. "
            "A gear located 150 mm from the right end transmits a tangential load of 1.6 kN and a radial load of 0.6 kN "
            "with pitch radius 55 mm. A downward point load of 500 N acts at midspan. Apply a torque of 70 N*m at the right end."
        )
        spec = build_spec(text)
        self.assertEqual(spec["class"], "shaft.analysis.segmented")
        self.assertEqual(len(spec["ambiguities"]), 1)
        self.assertIn("Assuming supports at shaft ends", spec["ambiguities"][0]["reason"])

        inputs = spec["inputs"]
        self.assertEqual(len(inputs["segments"]), 1)
        segment = inputs["segments"][0]
        self.assert_segment(segment, 0.9, 0.032)

        gear = next(ld for ld in inputs["loads"] if ld["type"] == "gear")
        expected_x = segment["length"] - 0.15
        self.assertTrue(math.isclose(gear["x"], expected_x, abs_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_t"], 1600.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["F_r"], 600.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(gear["r"], 0.055, rel_tol=1e-9))

        point = next(ld for ld in inputs["loads"] if ld["type"] == "point_force")
        self.assertTrue(math.isclose(point["x"], 0.45, abs_tol=1e-9))
        self.assertTrue(math.isclose(point["Fz"], -500.0, rel_tol=1e-9))

        torque = next(ld for ld in inputs["loads"] if ld["type"] == "torque")
        self.assertTrue(math.isclose(torque["x"], segment["length"], abs_tol=1e-9))
        self.assertTrue(math.isclose(torque["T"], 70.0, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
