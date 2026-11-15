// SPDX-License-Identifier: Apache-2.0
// SIMULATION-ONLY, non-safety-rated host reference. No MCU or actuator API.
#ifndef OCE_CTL01_COMMAND_GATE_HPP
#define OCE_CTL01_COMMAND_GATE_HPP

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace oce::ctl01 {

enum class State { disabled, armed, stopped, fault };
enum class Reason {
  disabled, armed, ok, estop, protective_fault, human_pause, manual_override,
  stale_heartbeat, invalid_command, arm_requires_zero, reset_requires_zero,
  reset_cause_active, reset_complete, command_saturated
};

struct Command {
  double speed_mps{0.0};
  double yaw_rate_rps{0.0};
};

struct Limits {
  double max_speed_mps{0.8};
  double max_yaw_rate_rps{0.9};
  double heartbeat_timeout_s{0.3};
};

struct Inputs {
  Command requested{};
  double heartbeat_age_s{0.0};
  bool estop{false};
  bool protective_fault{false};
  bool pause{false};
  bool manual_override{false};
  bool arm_request{false};
  bool reset_request{false};
};

struct Decision {
  State state{State::disabled};
  Command command{};
  std::vector<Reason> reasons{Reason::disabled};
};

class CommandGate final {
 public:
  explicit CommandGate(Limits limits) : limits_(limits) {
    if (!std::isfinite(limits.max_speed_mps) || limits.max_speed_mps <= 0.0 ||
        !std::isfinite(limits.max_yaw_rate_rps) || limits.max_yaw_rate_rps <= 0.0 ||
        !std::isfinite(limits.heartbeat_timeout_s) || limits.heartbeat_timeout_s <= 0.0) {
      throw std::invalid_argument("CommandGate limits must be finite and positive");
    }
  }

  Decision update(const Inputs& input) {
    std::vector<Reason> causes;
    const bool finite_command = std::isfinite(input.requested.speed_mps) &&
                                std::isfinite(input.requested.yaw_rate_rps);
    const bool finite_age = std::isfinite(input.heartbeat_age_s) && input.heartbeat_age_s >= 0.0;
    if (input.estop) causes.push_back(Reason::estop);
    if (input.protective_fault) causes.push_back(Reason::protective_fault);
    if (!finite_command || !finite_age) causes.push_back(Reason::invalid_command);
    if (finite_age && input.heartbeat_age_s > limits_.heartbeat_timeout_s) {
      causes.push_back(Reason::stale_heartbeat);
    }
    if (input.pause) causes.push_back(Reason::human_pause);
    if (input.manual_override) causes.push_back(Reason::manual_override);
    const bool protective_cause = std::any_of(causes.begin(), causes.end(), [](Reason reason) {
      return reason != Reason::human_pause && reason != Reason::manual_override;
    });
    if (protective_cause) {
      state_ = State::fault;
      latched_ = causes;
    } else if (!causes.empty()) {
      state_ = State::stopped;
      latched_ = causes;
    } else if (input.reset_request) {
      if (state_ == State::stopped || state_ == State::fault) {
        if (!zero(input.requested)) {
          latched_ = {Reason::reset_requires_zero};
        } else {
          state_ = State::disabled;
          latched_ = {Reason::reset_complete};
        }
      }
    } else if (state_ == State::stopped || state_ == State::fault) {
      // Clearing an input never resets a latched stop or resumes a command.
    } else if (state_ == State::disabled) {
      if (input.arm_request && zero(input.requested)) {
        state_ = State::armed;
        latched_ = {Reason::armed};
      } else if (input.arm_request) {
        latched_ = {Reason::arm_requires_zero};
      } else {
        latched_ = {Reason::disabled};
      }
    }
    if (state_ != State::armed) return {state_, {}, latched_};
    Command bounded{
        std::clamp(input.requested.speed_mps, -limits_.max_speed_mps, limits_.max_speed_mps),
        std::clamp(input.requested.yaw_rate_rps, -limits_.max_yaw_rate_rps, limits_.max_yaw_rate_rps)};
    latched_ = {Reason::ok};
    if (bounded.speed_mps != input.requested.speed_mps ||
        bounded.yaw_rate_rps != input.requested.yaw_rate_rps) {
      latched_.push_back(Reason::command_saturated);
    }
    return {state_, bounded, latched_};
  }

  State state() const { return state_; }

 private:
  static bool zero(const Command& command) {
    return std::abs(command.speed_mps) <= 1e-12 && std::abs(command.yaw_rate_rps) <= 1e-12;
  }
  Limits limits_;
  State state_{State::disabled};
  std::vector<Reason> latched_{Reason::disabled};
};

}  // namespace oce::ctl01
#endif
