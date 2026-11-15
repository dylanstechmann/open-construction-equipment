// SPDX-License-Identifier: Apache-2.0
// Host unit tests only; no target flashing or hardware integration.
#include "command_gate.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using oce::ctl01::Command;
using oce::ctl01::CommandGate;
using oce::ctl01::Inputs;
using oce::ctl01::Limits;
using oce::ctl01::Reason;
using oce::ctl01::State;

namespace {
int failures = 0;
int checks = 0;

void expect(bool condition, const std::string& message) {
  ++checks;
  if (!condition) {
    ++failures;
    std::cerr << "FAIL: " << message << static_cast<char>(10);
  }
}

bool has(const std::vector<Reason>& reasons, Reason wanted) {
  for (const auto reason : reasons) if (reason == wanted) return true;
  return false;
}

void expect_invalid_limits(const Limits& limits, const std::string& label) {
  bool rejected = false;
  try {
    CommandGate gate{limits};
    (void)gate;
  } catch (const std::invalid_argument& error) {
    rejected = std::string(error.what()).find("finite and positive") != std::string::npos;
  }
  expect(rejected, label);
}

void arm(CommandGate& gate) {
  Inputs input;
  input.arm_request = true;
  const auto decision = gate.update(input);
  expect(decision.state == State::armed, "zero-command arm succeeds");
  expect(decision.command.speed_mps == 0.0, "arming itself emits zero speed");
}
}

int main() {
  CommandGate boot{{0.8, 0.9, 0.3}};
  auto decision = boot.update({});
  expect(decision.state == State::disabled, "boot is disabled");
  expect(decision.command.speed_mps == 0.0 && decision.command.yaw_rate_rps == 0.0, "boot is zero");
  decision = boot.update(Inputs{{0.5, 0.0}, 0.0});
  expect(decision.state == State::disabled && decision.command.speed_mps == 0.0, "motion cannot bypass arming");
  arm(boot);
  decision = boot.update(Inputs{{2.0, -2.0}, 0.0});
  expect(std::abs(decision.command.speed_mps - 0.8) < 1e-12, "speed saturates explicitly");
  expect(std::abs(decision.command.yaw_rate_rps + 0.9) < 1e-12, "yaw rate saturates explicitly");
  expect(has(decision.reasons, Reason::command_saturated), "saturation is reported");

  Inputs estop_input{{0.4, 0.0}, 0.0};
  estop_input.estop = true;
  decision = boot.update(estop_input);
  expect(decision.state == State::fault && has(decision.reasons, Reason::estop), "estop faults and zeroes");
  decision = boot.update({});
  expect(decision.state == State::fault && decision.command.speed_mps == 0.0, "estop does not auto-resume");
  Inputs bad_reset{};
  bad_reset.reset_request = true;
  bad_reset.requested.speed_mps = 0.1;
  decision = boot.update(bad_reset);
  expect(decision.state == State::fault && has(decision.reasons, Reason::reset_requires_zero), "reset requires zero command");
  Inputs reset{};
  reset.reset_request = true;
  decision = boot.update(reset);
  expect(decision.state == State::disabled && has(decision.reasons, Reason::reset_complete), "deliberate reset disables");
  decision = boot.update({});
  expect(decision.state == State::disabled, "reset does not rearm");
  arm(boot);

  CommandGate paused{{0.8, 0.9, 0.3}};
  arm(paused);
  Inputs pause_input{{0.4, 0.0}, 0.0};
  pause_input.pause = true;
  decision = paused.update(pause_input);
  expect(decision.state == State::stopped && has(decision.reasons, Reason::human_pause), "human pause overrides motion");
  decision = paused.update({});
  expect(decision.state == State::stopped, "pause clearing does not resume");
  decision = paused.update(reset);
  expect(decision.state == State::disabled, "cleared pause permits deliberate reset");

  CommandGate watchdog{{0.8, 0.9, 0.3}};
  arm(watchdog);
  decision = watchdog.update(Inputs{{0.4, 0.0}, 0.31});
  expect(decision.state == State::fault && has(decision.reasons, Reason::stale_heartbeat), "stale heartbeat latches fault");
  decision = watchdog.update({});
  expect(decision.state == State::fault, "fresh heartbeat alone does not clear watchdog");

  CommandGate invalid{{0.8, 0.9, 0.3}};
  arm(invalid);
  const double nan = std::numeric_limits<double>::quiet_NaN();
  decision = invalid.update(Inputs{{nan, 0.0}, 0.0});
  expect(decision.state == State::fault && has(decision.reasons, Reason::invalid_command), "NaN command faults");

  CommandGate protective{{0.8, 0.9, 0.3}};
  arm(protective);
  Inputs protective_input{{0.4, 0.0}, 0.0};
  protective_input.protective_fault = true;
  decision = protective.update(protective_input);
  expect(decision.state == State::fault && has(decision.reasons, Reason::protective_fault), "protective fault wins");

  CommandGate override_gate{{0.8, 0.9, 0.3}};
  arm(override_gate);
  Inputs override_input{{0.4, 0.0}, 0.0};
  override_input.manual_override = true;
  decision = override_gate.update(override_input);
  expect(decision.state == State::stopped && has(decision.reasons, Reason::manual_override), "manual override overrides tracker");

  const double infinity = std::numeric_limits<double>::infinity();
  expect_invalid_limits(Limits{nan, 0.9, 0.3}, "NaN speed limit is rejected");
  expect_invalid_limits(Limits{0.8, nan, 0.3}, "NaN yaw limit is rejected");
  expect_invalid_limits(Limits{0.8, 0.9, nan}, "NaN timeout is rejected");
  expect_invalid_limits(Limits{infinity, 0.9, 0.3}, "infinite speed limit is rejected");
  expect_invalid_limits(Limits{0.8, -infinity, 0.3}, "infinite yaw limit is rejected");
  expect_invalid_limits(Limits{0.8, 0.9, infinity}, "infinite timeout is rejected");
  expect_invalid_limits(Limits{0.0, 0.9, 0.3}, "zero speed limit is rejected");
  expect_invalid_limits(Limits{0.8, 0.0, 0.3}, "zero yaw limit is rejected");
  expect_invalid_limits(Limits{0.8, 0.9, 0.0}, "zero timeout is rejected");
  expect_invalid_limits(Limits{-0.8, 0.9, 0.3}, "negative speed limit is rejected");
  expect_invalid_limits(Limits{0.8, -0.9, 0.3}, "negative yaw limit is rejected");
  expect_invalid_limits(Limits{0.8, 0.9, -0.3}, "negative timeout is rejected");

  if (failures != 0) {
    std::cerr << failures << " of " << checks << " checks failed" << static_cast<char>(10);
    return EXIT_FAILURE;
  }
  std::cout << "Firmware host checks passed: " << checks << static_cast<char>(10);
  return EXIT_SUCCESS;
}
