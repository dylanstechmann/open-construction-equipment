# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import FrozenInstanceError, replace
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from open_construction_equipment.config import ConfigError
from open_construction_equipment.physics import EvidenceStatus
from open_construction_equipment.powertrain import (
    HYDROGEN_LHV_KWH_PER_KG,
    ConstructionTask,
    EnergyFinding,
    FuelKind,
    HydrogenUseCase,
    LfpBatterySystem,
    MicrogridSimulator,
    PowertrainKind,
    PvSystem,
    SolarInterval,
    allocate_task_cost,
    battery_temperature_factor,
    compare_powertrains,
    estimate_free_field_noise,
    hydrogen_round_trip_efficiency,
    load_powertrain_input,
    parse_powertrain_input,
    powertrain_result_json,
    simulate_battery_path,
    simulate_fuel_path,
    simulate_hydrogen_path,
    write_powertrain_result,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "examples/powertrain/synthetic-microgrid.json"
SCHEMA_PATH = ROOT / "schemas/powertrain-input.schema.json"


def profile(*intervals):
    return tuple(SolarInterval(duration, solar, temperature) for duration, solar, temperature in intervals)


def task(task_id="T-1", shaft=8.0, auxiliary=2.0, efficiency=0.8, peak=12.0,
         heat=0.0, confined=False, solar_profile=None):
    return ConstructionTask(
        task_id, shaft, auxiliary, efficiency, peak, heat, confined,
        solar_profile if solar_profile is not None else profile((1.0, 0.0, 20.0)),
    )


class PowertrainTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
        self.model = parse_powertrain_input(copy.deepcopy(self.data))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pv = PvSystem(1000.0, 1.0, 1.0)

    def battery(self, **changes):
        values = dict(
            nominal_energy_kwh=100.0, minimum_stored_energy_kwh=0.0,
            maximum_stored_energy_kwh=20.0, initial_stored_energy_kwh=20.0,
            charge_efficiency=1.0, discharge_efficiency=1.0,
            maximum_charge_power_kw=100.0, maximum_discharge_power_kw=100.0,
            source_dba_at_reference_distance=None, reference_distance_m=None,
            receiver_target_dba=None, cold_reference_temperature_c=15.0,
            cold_derating_per_c=0.0, cutoff_temperature_c=-20.0,
        )
        values.update(changes)
        return LfpBatterySystem(**values)

    def hydrogen(self, **changes):
        values = dict(use_case=HydrogenUseCase.DAILY_CYCLING, maximum_electrolyzer_power_kw=10000.0,
                      maximum_reconversion_power_kw=10000.0)
        values.update(changes)
        return replace(self.model.hydrogen, **values)

    def diesel(self, **changes):
        return replace(self.model.fuels[0], **changes)

    def test_canonical_example_efficiencies_water_and_provenance(self):
        self.assertEqual(self.model.fuels[0].fuel_kind, FuelKind.DIESEL)
        self.assertEqual(self.model.fuels[1].fuel_kind, FuelKind.GASOLINE)
        battery_eta = (self.model.battery.charge_efficiency * self.model.battery.discharge_efficiency
                       * self.model.pv.ac_inverter_efficiency)
        self.assertAlmostEqual(battery_eta, 0.85248)
        self.assertTrue(0.84 < battery_eta < 0.86)
        h2_eta = hydrogen_round_trip_efficiency(
            self.model.hydrogen, self.model.pv.ac_inverter_efficiency, PowertrainKind.SOLAR_H2_PEMFC,
        )
        self.assertTrue(0.25 <= h2_eta <= 0.32)
        self.assertEqual(self.model.hydrogen.deionized_water_l_per_kg, 12)
        self.assertTrue(self.model.provenance.ai_authored)
        self.assertFalse(self.model.provenance.physical_validation_performed)

    def test_one_interval_hand_dispatch_and_discharge_loss_once(self):
        battery = self.battery(charge_efficiency=0.8, discharge_efficiency=0.9)
        work = task(solar_profile=profile((1.0, 5.0, 20.0)))
        result = simulate_battery_path(work, self.pv, battery, self.model.costs)
        self.assertEqual(result.required_electrical_energy_kwh, 12)
        self.assertEqual(result.solar_direct_kwh, 5)
        self.assertEqual(result.battery_discharge_kwh, 7)
        self.assertEqual(result.served_energy_kwh, 12)
        self.assertEqual(result.unserved_energy_kwh, 0)
        self.assertAlmostEqual(result.conversion_loss_heat_kwh, 7 / 0.9 - 7)
        self.assertEqual(result.solar_curtailed_kwh, 0)

    def test_duration_proportional_interval_load_and_direct_pv_first(self):
        work = task(solar_profile=profile((1.0, 3.0, 20.0), (3.0, 0.0, 20.0)))
        result = simulate_battery_path(work, self.pv, self.battery(), self.model.costs)
        self.assertEqual(result.solar_direct_kwh, 3)
        self.assertEqual(result.battery_discharge_kwh, 9)
        self.assertEqual(result.served_energy_kwh, 12)

    def test_charge_power_cap_loss_and_full_battery_curtailment(self):
        battery = self.battery(initial_stored_energy_kwh=10, charge_efficiency=0.5,
                               maximum_charge_power_kw=4)
        work = task(shaft=0, auxiliary=0, peak=0, solar_profile=profile((1.0, 10.0, 20.0)))
        result = simulate_battery_path(work, self.pv, battery, self.model.costs)
        self.assertEqual(result.solar_curtailed_kwh, 6)
        self.assertEqual(result.conversion_loss_heat_kwh, 2)
        full = simulate_battery_path(work, self.pv, self.battery(), self.model.costs)
        self.assertEqual(full.solar_curtailed_kwh, 10)
        self.assertEqual(full.conversion_loss_heat_kwh, 0)

    def test_battery_minimum_storage_and_power_cap_leave_unserved(self):
        empty = simulate_battery_path(task(), self.pv, self.battery(initial_stored_energy_kwh=0), self.model.costs)
        self.assertEqual(empty.served_energy_kwh, 0)
        self.assertEqual(empty.unserved_energy_kwh, 12)
        limited = simulate_battery_path(task(), self.pv, self.battery(maximum_discharge_power_kw=5), self.model.costs)
        self.assertEqual(limited.served_energy_kwh, 5)
        self.assertEqual(limited.unserved_energy_kwh, 7)
        self.assertIn(EnergyFinding.UNSERVED_ENERGY, limited.findings)

    def test_battery_temperature_factor_reference_cutoff_and_no_bonus(self):
        battery = self.battery(cold_derating_per_c=0.04)
        self.assertEqual(battery_temperature_factor(15, battery), 1)
        self.assertEqual(battery_temperature_factor(30, battery), 1)
        self.assertAlmostEqual(battery_temperature_factor(0, battery), 0.4)
        self.assertEqual(battery_temperature_factor(-20, battery), 0)
        self.assertEqual(battery_temperature_factor(-30, battery), 0)
        self.assertEqual(battery_temperature_factor(-10, self.battery(cold_derating_per_c=0.2)), 0)

    def test_cold_temperature_reduces_discharge_and_cutoff_eliminates_it(self):
        work = task(shaft=8, auxiliary=0, efficiency=1)
        warm = simulate_battery_path(work, self.pv, self.battery(initial_stored_energy_kwh=8), self.model.costs)
        cold_battery = self.battery(initial_stored_energy_kwh=8, cold_derating_per_c=0.04)
        cold_work = task(shaft=8, auxiliary=0, efficiency=1,
                         solar_profile=profile((1.0, 0.0, 0.0)))
        cold = simulate_battery_path(cold_work, self.pv, cold_battery, self.model.costs)
        self.assertEqual(warm.battery_discharge_kwh, 8)
        self.assertAlmostEqual(cold.battery_discharge_kwh, 3.2)
        cutoff_work = task(shaft=8, auxiliary=0, efficiency=1,
                           solar_profile=profile((1.0, 0.0, -20.0)))
        cutoff = simulate_battery_path(cutoff_work, self.pv, cold_battery, self.model.costs)
        self.assertEqual(cutoff.battery_discharge_kwh, 0)
        self.assertEqual(cutoff.unserved_energy_kwh, 8)

    def test_cold_derated_peak_power_flags_winter_utility(self):
        result = compare_powertrains(self.model)
        winter = next(
            item for item in result.task_results
            if item.task_id == "TASK-WINTER-UTILITY" and item.path is PowertrainKind.BATTERY_LFP
        )
        task_model = next(item for item in self.model.tasks if item.task_id == "TASK-WINTER-UTILITY")
        factor = battery_temperature_factor(
            task_model.solar_profile[0].ambient_temperature_c, self.model.battery,
        )
        self.assertAlmostEqual(factor, 0.4)
        self.assertAlmostEqual(self.model.battery.maximum_discharge_power_kw * factor, 18.0)
        self.assertEqual(task_model.peak_electric_power_kw, 28.0)
        self.assertIn(EnergyFinding.PEAK_POWER_EXCEEDED, winter.findings)

    def test_hydrogen_shared_surplus_chain_formula(self):
        system = self.hydrogen()
        expected = 0.7 * 0.5 * 0.925 / (1 + 0.7 * 4 / HYDROGEN_LHV_KWH_PER_KG)
        actual = hydrogen_round_trip_efficiency(system, 0.925, PowertrainKind.SOLAR_H2_PEMFC)
        self.assertAlmostEqual(actual, expected)
        ice = hydrogen_round_trip_efficiency(system, 0.925, PowertrainKind.SOLAR_H2_ICE)
        self.assertAlmostEqual(ice, expected * 0.3 / 0.5)
        with self.assertRaises(ConfigError):
            hydrogen_round_trip_efficiency(system, 0.925, PowertrainKind.BATTERY_LFP)

    def test_hydrogen_out_of_range_is_warning_not_clamped(self):
        model = replace(self.model, hydrogen=self.hydrogen(pem_fuel_cell_lhv_efficiency=0.9))
        result = compare_powertrains(model)
        pem = next(item for item in result.task_results if item.path is PowertrainKind.SOLAR_H2_PEMFC)
        self.assertGreater(pem.electrical_round_trip_efficiency, 0.32)
        self.assertTrue(any("WARNING" in note and "25-32%" in note for note in result.comparison_notes))

    def test_hydrogen_production_after_full_battery_and_water(self):
        specific = HYDROGEN_LHV_KWH_PER_KG / 0.7 + 4
        work = task(shaft=0, auxiliary=0, peak=0,
                    solar_profile=profile((1.0, 2 * specific, 20.0)))
        result = simulate_hydrogen_path(work, self.pv, self.battery(), self.hydrogen(initial_stored_kg=0),
                                        PowertrainKind.SOLAR_H2_PEMFC, self.model.costs)
        self.assertAlmostEqual(result.hydrogen_produced_kg, 2)
        self.assertAlmostEqual(result.hydrogen_solar_input_kwh, 2 * specific)
        self.assertAlmostEqual(result.deionized_water_l, 24)
        self.assertAlmostEqual(result.solar_curtailed_kwh, 0)
        self.assertEqual(result.solar_direct_kwh, 0)
        self.assertEqual(result.battery_discharge_kwh, 0)

    def test_hydrogen_uses_surplus_after_charge_power_limit(self):
        specific = HYDROGEN_LHV_KWH_PER_KG / 0.7 + 4
        battery = self.battery(initial_stored_energy_kwh=0, maximum_stored_energy_kwh=100,
                               maximum_charge_power_kw=2)
        work = task(shaft=0, auxiliary=0, peak=0,
                    solar_profile=profile((1.0, 2 + specific, 20.0)))
        result = simulate_hydrogen_path(work, self.pv, battery, self.hydrogen(initial_stored_kg=0),
                                        PowertrainKind.SOLAR_H2_PEMFC, self.model.costs)
        self.assertAlmostEqual(result.hydrogen_produced_kg, 1)
        self.assertAlmostEqual(result.solar_curtailed_kwh, 0)

    def test_full_hydrogen_storage_produces_nothing(self):
        work = task(shaft=0, auxiliary=0, peak=0, solar_profile=profile((1.0, 100.0, 20.0)))
        full = self.hydrogen(initial_stored_kg=self.model.hydrogen.storage_capacity_kg)
        result = simulate_hydrogen_path(work, self.pv, self.battery(), full,
                                        PowertrainKind.SOLAR_H2_PEMFC, self.model.costs)
        self.assertEqual(result.hydrogen_produced_kg, 0)
        self.assertEqual(result.deionized_water_l, 0)
        self.assertEqual(result.solar_curtailed_kwh, 100)

    def test_hydrogen_deficit_mass_and_single_converter_application(self):
        ac_per_kg = HYDROGEN_LHV_KWH_PER_KG * 0.5  # Unit test inverter is one.
        work = task(shaft=ac_per_kg, auxiliary=0, efficiency=1, peak=10)
        result = simulate_hydrogen_path(work, self.pv, self.battery(initial_stored_energy_kwh=0),
                                        self.hydrogen(initial_stored_kg=1),
                                        PowertrainKind.SOLAR_H2_PEMFC, self.model.costs)
        self.assertAlmostEqual(result.hydrogen_consumed_kg, 1)
        self.assertAlmostEqual(result.hydrogen_electrical_output_kwh, ac_per_kg)
        self.assertAlmostEqual(result.served_energy_kwh, ac_per_kg)
        self.assertAlmostEqual(result.unserved_energy_kwh, 0)

    def test_hydrogen_ice_uses_distinct_efficiency(self):
        pem = simulate_hydrogen_path(task(), self.pv, self.battery(initial_stored_energy_kwh=0),
                                     self.hydrogen(initial_stored_kg=2), PowertrainKind.SOLAR_H2_PEMFC,
                                     self.model.costs)
        ice = simulate_hydrogen_path(task(), self.pv, self.battery(initial_stored_energy_kwh=0),
                                     self.hydrogen(initial_stored_kg=2), PowertrainKind.SOLAR_H2_ICE,
                                     self.model.costs)
        self.assertAlmostEqual(ice.hydrogen_electrical_output_kwh, 12)
        self.assertAlmostEqual(pem.hydrogen_electrical_output_kwh, 12)
        self.assertAlmostEqual(ice.hydrogen_consumed_kg, pem.hydrogen_consumed_kg * 0.5 / 0.3)
        self.assertLess(ice.electrical_round_trip_efficiency, pem.electrical_round_trip_efficiency)

    def test_empty_hydrogen_store_cannot_recommence(self):
        result = simulate_hydrogen_path(task(), self.pv, self.battery(initial_stored_energy_kwh=0),
                                        self.hydrogen(initial_stored_kg=0), PowertrainKind.SOLAR_H2_PEMFC,
                                        self.model.costs)
        self.assertEqual(result.hydrogen_consumed_kg, 0)
        self.assertEqual(result.hydrogen_electrical_output_kwh, 0)
        self.assertEqual(result.unserved_energy_kwh, 12)

    def test_water_boundaries_nine_and_fifteen(self):
        specific = HYDROGEN_LHV_KWH_PER_KG / 0.7 + 4
        work = task(shaft=0, auxiliary=0, peak=0, solar_profile=profile((1.0, specific, 20.0)))
        for water in (9, 15):
            with self.subTest(water=water):
                result = simulate_hydrogen_path(
                    work, self.pv, self.battery(), self.hydrogen(initial_stored_kg=0, deionized_water_l_per_kg=water),
                    PowertrainKind.SOLAR_H2_PEMFC, self.model.costs,
                )
                self.assertAlmostEqual(result.deionized_water_l, water)

    def test_seasonal_curtailment_captures_post_battery_surplus(self):
        result = compare_powertrains(self.model)
        self.assertIs(result.hydrogen_niche, HydrogenUseCase.SEASONAL_CURTAILMENT)
        seasonal = next(item for item in result.task_results
                        if item.task_id == "TASK-SEASONAL-SURPLUS" and item.path is PowertrainKind.SOLAR_H2_PEMFC)
        battery = next(item for item in result.task_results
                       if item.task_id == "TASK-SEASONAL-SURPLUS" and item.path is PowertrainKind.BATTERY_LFP)
        self.assertGreater(seasonal.hydrogen_solar_input_kwh, 0)
        self.assertLess(seasonal.solar_curtailed_kwh, battery.solar_curtailed_kwh)
        self.assertTrue(any("otherwise-curtailed" in note for note in result.comparison_notes))

    def test_winter_chp_is_capped_by_demand_and_fuel_input(self):
        ac_per_kg = HYDROGEN_LHV_KWH_PER_KG * 0.5
        for demand in (5.0, 100.0):
            with self.subTest(demand=demand):
                work = task(shaft=ac_per_kg, auxiliary=0, efficiency=1, heat=demand)
                result = simulate_hydrogen_path(
                    work, self.pv, self.battery(initial_stored_energy_kwh=0),
                    self.hydrogen(initial_stored_kg=1, use_case=HydrogenUseCase.WINTER_CHP),
                    PowertrainKind.SOLAR_H2_PEMFC, self.model.costs,
                )
                expected = min(demand, HYDROGEN_LHV_KWH_PER_KG * 0.35)
                self.assertAlmostEqual(result.recovered_heat_kwh, expected)
                self.assertAlmostEqual(result.unmet_heat_kwh, demand - expected)

    def test_daily_battery_preference_is_transparent_arithmetic(self):
        model = replace(self.model, tasks=(task(),), pv=self.pv,
                        hydrogen=self.hydrogen(use_case=HydrogenUseCase.DAILY_CYCLING))
        result = compare_powertrains(model)
        self.assertTrue(result.daily_battery_preferred)
        note = next(note for note in result.comparison_notes if note.startswith("Daily arithmetic"))
        self.assertIn("loss rates", note)
        self.assertIn("not procurement advice", note)

    def test_fuel_hand_arithmetic_refills_delivery_and_operating_cost(self):
        work = task(shaft=100, auxiliary=0, efficiency=1, peak=100)
        fuel = self.diesel(tank_capacity_l=10)
        raw = simulate_fuel_path(work, self.pv, fuel, PowertrainKind.DIESEL_ICE, self.model.costs)
        self.assertAlmostEqual(raw.fuel_consumed_l, 100 / 3.6)
        self.assertEqual(raw.refill_events, 2)
        self.assertEqual(raw.refill_delivery_km, 240)
        model = replace(self.model, tasks=(work,), pv=self.pv, fuels=(fuel, self.model.fuels[1]))
        allocated, operating = allocate_task_cost(PowertrainKind.DIESEL_ICE, 1, raw, model)
        self.assertAlmostEqual(allocated, (18000 + 7000) / 4000)
        self.assertAlmostEqual(operating, raw.fuel_consumed_l * 1.8 + 240 * 0.9 + 1.2)

    def test_zero_deficit_zero_fuel_and_refills(self):
        work = task(shaft=0, auxiliary=0, peak=0)
        result = simulate_fuel_path(work, self.pv, self.diesel(), PowertrainKind.DIESEL_ICE, self.model.costs)
        self.assertEqual(result.fuel_consumed_l, 0)
        self.assertEqual(result.refill_events, 0)
        self.assertEqual(result.refill_delivery_km, 0)

    def test_generator_power_cap_and_peak_flag(self):
        work = task(shaft=100, auxiliary=0, efficiency=1, peak=50)
        result = simulate_fuel_path(work, self.pv, self.diesel(maximum_electrical_power_kw=40),
                                    PowertrainKind.DIESEL_ICE, self.model.costs)
        self.assertEqual(result.served_energy_kwh, 40)
        self.assertEqual(result.unserved_energy_kwh, 60)
        self.assertIn(EnergyFinding.PEAK_POWER_EXCEEDED, result.findings)
        with self.assertRaises(ConfigError):
            simulate_fuel_path(work, self.pv, self.diesel(), PowertrainKind.GASOLINE_ICE, self.model.costs)

    def test_free_field_noise_hand_formula_and_reference_bound(self):
        result = estimate_free_field_noise(80, 2, 60, False)
        self.assertAlmostEqual(result.free_field_geometric_distance_m, 20)
        self.assertEqual(estimate_free_field_noise(80, 2, 80, False).free_field_geometric_distance_m, 2)
        self.assertEqual(estimate_free_field_noise(80, 2, 90, False).free_field_geometric_distance_m, 2)
        confined = estimate_free_field_noise(40, 2, 50, True)
        self.assertTrue(confined.confined_space_review_required)

    def test_electric_noise_null_or_uses_optional_triple(self):
        silent_input = simulate_battery_path(task(), self.pv, self.battery(), self.model.costs)
        self.assertIsNone(silent_input.noise)
        acoustic = self.battery(source_dba_at_reference_distance=60, reference_distance_m=2,
                                receiver_target_dba=50)
        result = simulate_battery_path(task(), self.pv, acoustic, self.model.costs)
        self.assertAlmostEqual(result.noise.free_field_geometric_distance_m, 2 * 10**0.5)

    def test_confined_zero_load_fossil_still_requires_exhaust_review(self):
        work = task(shaft=0, auxiliary=0, peak=0, confined=True)
        result = simulate_fuel_path(work, self.pv, self.diesel(), PowertrainKind.DIESEL_ICE, self.model.costs)
        self.assertIn(EnergyFinding.CONFINED_EXHAUST_REVIEW, result.findings)
        self.assertTrue(result.noise.confined_space_review_required)
        self.assertEqual(result.fuel_consumed_l, 0)
        serialized = powertrain_result_json(compare_powertrains(replace(self.model, tasks=(work,), pv=self.pv)))
        self.assertNotIn("safeEntry", serialized)
        self.assertNotIn("exposureDose", serialized)

    def test_system_capex_component_sets_and_allocated_cost(self):
        result = compare_powertrains(self.model)
        capex = {item.path: item for item in result.system_capex_by_path}
        self.assertEqual(capex[PowertrainKind.BATTERY_LFP].component_keys, ("solar_capex", "battery_capex"))
        self.assertIn("pem_fuel_cell_capex", capex[PowertrainKind.SOLAR_H2_PEMFC].component_keys)
        self.assertNotIn("h2_ice_capex", capex[PowertrainKind.SOLAR_H2_PEMFC].component_keys)
        self.assertIn("h2_ice_capex", capex[PowertrainKind.SOLAR_H2_ICE].component_keys)
        self.assertNotIn("pem_fuel_cell_capex", capex[PowertrainKind.SOLAR_H2_ICE].component_keys)
        for path in (PowertrainKind.DIESEL_ICE, PowertrainKind.GASOLINE_ICE):
            self.assertNotIn("hydrogen_storage_capex", capex[path].component_keys)
        work = self.model.tasks[0]
        battery_result = next(item for item in result.task_results
                              if item.task_id == work.task_id and item.path is PowertrainKind.BATTERY_LFP)
        self.assertAlmostEqual(battery_result.allocated_capex, (18000 + 24000) * 4 / 4000)
        self.assertAlmostEqual(battery_result.operating_cost, 0.8 * 4)
        self.assertNotEqual(battery_result.allocated_capex, capex[PowertrainKind.BATTERY_LFP].amount)

    def test_hydrogen_operating_cost_includes_water_battery_and_inspection(self):
        result = compare_powertrains(self.model)
        item = next(item for item in result.task_results
                    if item.task_id == "TASK-SEASONAL-SURPLUS" and item.path is PowertrainKind.SOLAR_H2_PEMFC)
        expected = item.deionized_water_l * 0.03 + 8 * (0.8 + 1.5)
        self.assertAlmostEqual(item.operating_cost, expected)

    def test_task_order_and_path_state_isolation(self):
        first = task("FIRST")
        second = task("SECOND")
        model = replace(self.model, tasks=(first, second), pv=self.pv)
        result = compare_powertrains(model)
        self.assertEqual([item.task_id for item in result.task_results[::5]], ["FIRST", "SECOND"])
        for index in range(5):
            left, right = result.task_results[index], result.task_results[index + 5]
            self.assertIs(left.path, right.path)
            self.assertEqual(left.served_energy_kwh, right.served_energy_kwh)
            self.assertEqual(left.battery_discharge_kwh, right.battery_discharge_kwh)
            self.assertEqual(left.hydrogen_consumed_kg, right.hydrogen_consumed_kg)

    def test_every_path_energy_closure_and_hydrogen_findings(self):
        result = MicrogridSimulator().run(self.model)
        self.assertEqual(len(result.task_results), 15)
        for item in result.task_results:
            with self.subTest(task=item.task_id, path=item.path):
                self.assertAlmostEqual(item.served_energy_kwh + item.unserved_energy_kwh,
                                       item.required_electrical_energy_kwh, delta=1e-9)
                self.assertGreaterEqual(item.conversion_loss_heat_kwh, 0)
                self.assertGreaterEqual(item.refill_delivery_km, 0)
                if item.path in (PowertrainKind.SOLAR_H2_PEMFC, PowertrainKind.SOLAR_H2_ICE):
                    self.assertIn(EnergyFinding.HYDROGEN_REVIEW_REQUIRED, item.findings)

    def test_zero_energy_task_is_explicit_and_conserved(self):
        work = task(shaft=0, auxiliary=0, peak=0)
        result = compare_powertrains(replace(self.model, tasks=(work,), pv=self.pv))
        for item in result.task_results:
            self.assertEqual(item.required_electrical_energy_kwh, 0)
            self.assertEqual(item.served_energy_kwh, 0)
            self.assertEqual(item.unserved_energy_kwh, 0)

    def test_parser_rejects_unknown_missing_boolean_nonfinite_and_duplicate_tasks(self):
        changes = []
        unknown = copy.deepcopy(self.data); unknown["extra"] = 1; changes.append(unknown)
        missing = copy.deepcopy(self.data); del missing["pv"]; changes.append(missing)
        boolean = copy.deepcopy(self.data); boolean["pv"]["nameplate_kW"] = True; changes.append(boolean)
        duplicate = copy.deepcopy(self.data); duplicate["tasks"].append(copy.deepcopy(duplicate["tasks"][0])); changes.append(duplicate)
        for value in (float("nan"), float("inf"), 10**400):
            changed = copy.deepcopy(self.data)
            changed["battery"]["nominalEnergy_kWh"] = value
            changes.append(changed)
        for changed in changes:
            with self.subTest(changed=str(changed)[:100]), self.assertRaises(ConfigError):
                parse_powertrain_input(changed)

    def test_parser_rejects_invalid_capacities_water_efficiencies_and_profiles(self):
        mutations = (
            ("battery", "maximumStoredEnergy_kWh", 12),
            ("battery", "initialStoredEnergy_kWh", 109),
            ("hydrogen", "initialStored_kg", 21),
            ("hydrogen", "deionizedWater_l_per_kg", 8.9),
            ("hydrogen", "deionizedWater_l_per_kg", 15.1),
            ("hydrogen", "electrolyzerLhvEfficiency", 0),
            ("pv", "acInverterEfficiency", 0),
        )
        for section, key, value in mutations:
            with self.subTest(section=section, key=key, value=value):
                changed = copy.deepcopy(self.data)
                changed[section][key] = value
                with self.assertRaises(ConfigError):
                    parse_powertrain_input(changed)
        changed = copy.deepcopy(self.data)
        changed["tasks"][0]["solarProfile"] = []
        with self.assertRaises(ConfigError):
            parse_powertrain_input(changed)

    def test_parser_enforces_acoustic_triple_fuel_order_currency_and_provenance(self):
        changed = copy.deepcopy(self.data)
        changed["battery"]["referenceDistance_m"] = 7
        with self.assertRaises(ConfigError):
            parse_powertrain_input(changed)
        changed = copy.deepcopy(self.data)
        changed["fuels"].reverse()
        with self.assertRaises(ConfigError):
            parse_powertrain_input(changed)
        for currency in ("usd", "US", "USDD"):
            changed = copy.deepcopy(self.data); changed["costs"]["currency"] = currency
            with self.subTest(currency=currency), self.assertRaises(ConfigError):
                parse_powertrain_input(changed)
        changed = copy.deepcopy(self.data); changed["provenance"]["siteSupplied"] = True
        with self.assertRaises(ConfigError):
            parse_powertrain_input(changed)

    def test_strict_file_loader_rejects_duplicate_keys_and_nonstandard_numbers(self):
        duplicate = Path(self.temp.name) / "duplicate.json"
        duplicate.write_text('{"analysisId":"x","analysisId":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "duplicate JSON key"):
            load_powertrain_input(duplicate)
        nan = Path(self.temp.name) / "nan.json"
        nan.write_text('{"value":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "non-standard JSON"):
            load_powertrain_input(nan)

    def test_result_determinism_output_units_money_and_gates(self):
        result = compare_powertrains(self.model)
        text = powertrain_result_json(result)
        self.assertEqual(text, powertrain_result_json(compare_powertrains(load_powertrain_input(INPUT_PATH))))
        decoded = json.loads(text)
        self.assertIn("requiredElectricalEnergy_kWh", decoded["taskResults"][0])
        self.assertIn("refillDelivery_km", decoded["taskResults"][0])
        self.assertIn("noise", decoded["taskResults"][0])
        self.assertIs(result.status, EvidenceStatus.SIMULATED_UNREVIEWED)
        self.assertFalse(result.physical_validation_performed)
        self.assertFalse(result.operational_release)
        gates = " ".join(result.unresolved_human_gate_ids)
        for discipline in ("ENERGY", "ELECTRICAL", "HYDROGEN", "FIRE", "NOISE", "AHJ"):
            self.assertIn(discipline, gates)
        path = write_powertrain_result(result, Path(self.temp.name) / "nested")
        self.assertEqual(path.read_bytes(), text.encode("utf-8"))
        self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_serialization_rejects_energy_closure_before_output_creation(self):
        result = compare_powertrains(self.model)
        broken = replace(result, task_results=(replace(result.task_results[0], served_energy_kwh=999),)
                         + result.task_results[1:])
        with self.assertRaisesRegex(ConfigError, "energy closure"):
            powertrain_result_json(broken)
        destination = Path(self.temp.name) / "not-created"
        with self.assertRaises(ConfigError):
            write_powertrain_result(broken, destination)
        self.assertFalse(destination.exists())

    def test_result_serializer_rejects_status_release_and_gate_mutations(self):
        result = compare_powertrains(self.model)
        mutations = (
            {"status": "REVIEWED"},
            {"physical_validation_performed": True},
            {"operational_release": True},
            {"unresolved_human_gate_ids": ()},
        )
        for changes in mutations:
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                powertrain_result_json(replace(result, **changes))

    def test_models_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.model.analysis_id = "changed"
        result = compare_powertrains(self.model)
        with self.assertRaises(FrozenInstanceError):
            result.task_results[0].served_energy_kwh = 0

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional jsonschema is not installed")
    def test_json_schema_validates_example_and_rejects_invalid(self):
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate(self.data)
        for mutate in (
            lambda value: value["provenance"].update(statement=" \n"),
            lambda value: value["tasks"][0].update(taskId=" \t"),
            lambda value: value["hydrogen"].update(deionizedWater_l_per_kg=16),
            lambda value: value.update(extra=True),
        ):
            changed = copy.deepcopy(self.data)
            mutate(changed)
            self.assertFalse(validator.is_valid(changed))


if __name__ == "__main__":
    unittest.main()
