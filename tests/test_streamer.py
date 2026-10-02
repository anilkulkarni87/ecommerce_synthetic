"""Tests for EventStreamer module."""

from pathlib import Path
import pytest

from ecommerce_synth.streamer import EventStreamer, StreamEvent


def test_event_streamer_loading(tmp_path: Path):
    from ecommerce_synth.config import load_config
    from ecommerce_synth.orchestrator import Orchestrator

    output_dir = tmp_path / "stream_test_dataset"
    config = load_config(tier_name="small", seed=55, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run(only=["customers", "products", "orders", "clickstream"])

    streamer = EventStreamer(data_dir=output_dir, limit=50)
    assert streamer.total_events > 0
    assert streamer.total_events <= 50


def test_event_streamer_to_jsonl(tmp_path: Path):
    from ecommerce_synth.config import load_config
    from ecommerce_synth.orchestrator import Orchestrator

    output_dir = tmp_path / "stream_test_dataset2"
    config = load_config(tier_name="small", seed=56, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run(only=["customers", "products", "orders", "clickstream"])

    streamer = EventStreamer(data_dir=output_dir, limit=10)
    jsonl_file = output_dir / "streamed.jsonl"

    events_received: list[StreamEvent] = []

    streamer.stream(
        speed=0,
        output_file=jsonl_file,
        raw_json=True,
        on_event=lambda e: events_received.append(e),
    )

    assert len(events_received) == 10
    assert jsonl_file.exists()

    with open(jsonl_file) as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 10
