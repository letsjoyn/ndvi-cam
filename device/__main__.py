from __future__ import annotations

import argparse
import logging

from .agent import DeviceAgent
from .api import FieldScopeApi
from .cameras import Picamera2CameraPair, SimulatedCameraPair
from .config import AgentConfig
from .registration import PairRegistrar
from .sensors import NullSensorSuite, SimulatedSensorSuite


def build_agent(config: AgentConfig) -> DeviceAgent:
    backend = FieldScopeApi(
        config.api_base_url,
        config.device_id,
        config.device_key,
        verify_tls=config.verify_tls,
    )
    if config.simulate:
        cameras = SimulatedCameraPair()
        sensors = SimulatedSensorSuite(config.simulated_illuminance_lux)
    else:
        cameras = Picamera2CameraPair(
            rgb_index=config.rgb_camera_index,
            nir_index=config.nir_camera_index,
        )
        sensors = NullSensorSuite()
    registrar = PairRegistrar.load(config.registration_file)
    return DeviceAgent(config, backend, cameras, sensors, registrar)


def main() -> None:
    parser = argparse.ArgumentParser(description="FieldScope Raspberry Pi agent")
    parser.add_argument(
        "--config",
        default="device/config.example.json",
        help="Path to the agent JSON configuration",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Capture, upload, heartbeat, and exit",
    )
    parser.add_argument(
        "--flush-only",
        action="store_true",
        help="Upload queued captures without taking a new image",
    )
    parser.add_argument(
        "--command-once",
        action="store_true",
        help="Claim and process at most one remote command, then exit",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = AgentConfig.load(args.config)
    agent = build_agent(config)
    try:
        if args.flush_only:
            agent.refresh_profile(force=True)
            agent.flush_queue()
            agent.send_heartbeat()
        elif args.command_once:
            agent.refresh_profile(force=True)
            agent.flush_queue()
            agent.process_next_command()
            agent.send_heartbeat()
        elif args.once:
            agent.run_once(reason="cli")
        else:
            agent.run_forever()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
