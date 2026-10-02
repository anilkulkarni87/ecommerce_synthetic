"""Real-time event streaming engine for synthetic ecommerce data.

Allows replaying clickstream sessions and POS/online orders sequentially
in chronological order to simulate real-time live events.

Supports multiple output sinks:
- stdout (JSON Lines or formatted Rich output)
- File (appended .jsonl)
- HTTP Webhook (POST JSON to an endpoint)
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Generator

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _json_serial(obj: Any) -> str:
    """JSON serializer for dates and datetimes."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


@dataclass
class StreamEvent:
    """Normalized live event envelope."""

    event_id: str
    timestamp: datetime
    stream_type: str  # 'clickstream', 'order_online', 'order_instore'
    event_name: str  # 'page_view', 'add_to_cart', 'order_created', etc.
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "stream_type": self.stream_type,
            "event_name": self.event_name,
            "data": self.payload,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=_json_serial)


class EventStreamer:
    """Loads and streams historical events in simulated real time."""

    def __init__(
        self,
        data_dir: Path | str,
        sources: list[str] | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

        self.sources = sources or ["clickstream", "orders_online", "orders_instore"]
        self.event_type_filter = event_type
        self.limit = limit
        self._events: list[StreamEvent] = []

        self._load_and_prepare_events()

    def _load_and_prepare_events(self) -> None:
        """Load Parquet tables, normalize to StreamEvent, and sort chronologically."""
        raw_events: list[StreamEvent] = []

        # 1. Clickstream
        if "clickstream" in self.sources:
            cs_path = self.data_dir / "clickstream.parquet"
            if cs_path.exists():
                df = pl.read_parquet(cs_path)
                for row in df.iter_rows(named=True):
                    etype = row.get("event_type", "unknown")
                    if self.event_type_filter and etype != self.event_type_filter:
                        continue

                    ts = row.get("event_timestamp")
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)

                    raw_events.append(
                        StreamEvent(
                            event_id=row.get("event_id", ""),
                            timestamp=ts,
                            stream_type="clickstream",
                            event_name=etype,
                            payload=row,
                        )
                    )

        # 2. Online Orders
        if "orders_online" in self.sources or "orders" in self.sources:
            oo_path = self.data_dir / "orders_online.parquet"
            if oo_path.exists():
                df = pl.read_parquet(oo_path)
                for row in df.iter_rows(named=True):
                    ts = row.get("order_date")
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)

                    raw_events.append(
                        StreamEvent(
                            event_id=row.get("order_id", ""),
                            timestamp=ts,
                            stream_type="order_online",
                            event_name="online_order_created",
                            payload=row,
                        )
                    )

        # 3. In-Store Orders
        if "orders_instore" in self.sources or "orders" in self.sources:
            io_path = self.data_dir / "orders_instore.parquet"
            if io_path.exists():
                df = pl.read_parquet(io_path)
                for row in df.iter_rows(named=True):
                    ts = row.get("transaction_date")
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)

                    raw_events.append(
                        StreamEvent(
                            event_id=row.get("transaction_id", ""),
                            timestamp=ts,
                            stream_type="order_instore",
                            event_name="pos_transaction_created",
                            payload=row,
                        )
                    )

        # Sort chronologically by timestamp
        raw_events.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min)

        if self.limit:
            raw_events = raw_events[: self.limit]

        self._events = raw_events

    @property
    def total_events(self) -> int:
        return len(self._events)

    def stream(
        self,
        speed: float = 1.0,
        interval_ms: int | None = None,
        max_delay_sec: float = 2.0,
        webhook_url: str | None = None,
        output_file: Path | str | None = None,
        raw_json: bool = False,
        loop: bool = False,
        on_event: Callable[[StreamEvent], None] | None = None,
    ) -> None:
        """Stream events to selected sinks.

        Args:
            speed: Simulation speed multiplier. E.g. speed=100 replays 100x faster
                than real time. speed=0 streams immediately with no delay.
            interval_ms: If set, sleeps fixed milliseconds between events
                instead of delta calculation.
            max_delay_sec: Caps the maximum real sleep between distant events.
            webhook_url: Optional HTTP endpoint to POST events to.
            output_file: Optional file path to append events to (.jsonl).
            raw_json: If True, prints pure NDJSON to stdout instead of Rich styling.
            loop: If True, restarts stream from beginning when finished.
            on_event: Optional callback hook invoked on each event.
        """
        if not self._events:
            console.print("[yellow]No events found matching the criteria.[/yellow]")
            return

        out_fp = open(output_file, "a") if output_file else None

        if not raw_json:
            console.print(
                Panel(
                    f"[bold cyan]🌊 Live Event Streamer[/bold cyan]\n"
                    f"Dataset: [bold]{self.data_dir}[/bold]\n"
                    f"Total Events to Stream: [green]{len(self._events):,}[/green]\n"
                    f"Mode: [yellow]{f'Interval {interval_ms}ms' if interval_ms else f'Speed {speed}x' if speed > 0 else 'Burst (no delay)'}[/yellow]\n"
                    f"Sinks: [magenta]{'Webhook: ' + webhook_url if webhook_url else 'stdout'}{', File: ' + str(output_file) if output_file else ''}[/magenta]",
                    border_style="cyan",
                )
            )

        events_emitted = 0
        start_clock = time.time()

        try:
            while True:
                last_event_time: datetime | None = None

                for event in self._events:
                    # Delay calculation
                    if interval_ms is not None and interval_ms > 0:
                        time.sleep(interval_ms / 1000.0)
                    elif speed > 0 and last_event_time and event.timestamp:
                        delta = (event.timestamp - last_event_time).total_seconds()
                        if delta > 0:
                            sleep_duration = min(max_delay_sec, delta / speed)
                            if sleep_duration > 0.001:
                                time.sleep(sleep_duration)

                    last_event_time = event.timestamp

                    # Sinks
                    event_json = event.to_json()

                    # 1. Output file
                    if out_fp:
                        out_fp.write(event_json + "\n")
                        out_fp.flush()

                    # 2. Webhook
                    if webhook_url:
                        self._post_webhook(webhook_url, event_json)

                    # 3. Custom callback
                    if on_event:
                        on_event(event)

                    # 4. Stdout
                    if raw_json:
                        print(event_json, flush=True)
                    else:
                        self._print_rich_event(event)

                    events_emitted += 1

                if not loop:
                    break

        except KeyboardInterrupt:
            if not raw_json:
                console.print("\n[yellow]Stream interrupted by user.[/yellow]")
        finally:
            if out_fp:
                out_fp.close()

        elapsed = time.time() - start_clock
        rate = (events_emitted / elapsed) if elapsed > 0 else 0.0

        if not raw_json:
            console.print(
                f"\n[bold green]✓ Stream finished![/bold green] "
                f"Emitted [bold]{events_emitted:,}[/bold] events in {elapsed:.1f}s ({rate:.1f} events/sec)\n"
            )

    def _post_webhook(self, url: str, json_str: str) -> None:
        """Post event JSON to webhook endpoint."""
        try:
            req = urllib.request.Request(
                url,
                data=json_str.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                pass
        except Exception as e:
            # Non-blocking error display
            pass

    def _print_rich_event(self, event: StreamEvent) -> None:
        """Print styled event to the terminal."""
        ts_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S") if event.timestamp else "N/A"

        color_map = {
            "clickstream": "cyan",
            "order_online": "green",
            "order_instore": "magenta",
        }
        color = color_map.get(event.stream_type, "white")

        detail = ""
        if event.stream_type == "clickstream":
            url = event.payload.get("page_url", "")
            dev = event.payload.get("device_type", "")
            detail = f"url=[dim]{url}[/dim] dev={dev}"
        elif event.stream_type == "order_online":
            amt = event.payload.get("total_amount", 0.0)
            status = event.payload.get("status", "")
            detail = f"total=[bold yellow]${amt:.2f}[/bold yellow] status={status}"
        elif event.stream_type == "order_instore":
            amt = event.payload.get("total_amount", 0.0)
            store = event.payload.get("store_id", "")
            detail = f"total=[bold yellow]${amt:.2f}[/bold yellow] store={store}"

        console.print(
            f"[dim]{ts_str}[/dim] [{color}]{event.stream_type.upper():<14}[/{color}] "
            f"[bold]{event.event_name:<22}[/bold] {detail}"
        )
