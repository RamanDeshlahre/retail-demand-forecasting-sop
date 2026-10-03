import unittest

import numpy as np

from src.pipeline import inventory_policy


class PlanningInvariants(unittest.TestCase):
    def test_simulated_demand_is_served_or_lost(self):
        forecasts = np.array([8.] * 28)
        demand = np.array([6., 10., 8., 12.] * 7)
        result = inventory_policy(forecasts, demand, initial_stock=18)
        self.assertAlmostEqual(result["served"] + result["lost"], result["demand"])
        self.assertEqual(result["days"], 25)
        self.assertGreaterEqual(result["waste"], 0)

    def test_zero_forecast_does_not_generate_new_orders(self):
        result = inventory_policy(np.zeros(28), np.ones(28), initial_stock=0)
        self.assertEqual(result["ordered"], 0)
        self.assertEqual(result["served"], 0)


if __name__ == "__main__":
    unittest.main()
