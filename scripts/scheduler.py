"""Scheduler simple pour lancer les synchronisations à intervalle régulier."""

import argparse
import asyncio
import os

from scripts.sync_legal_feed import synchronize as synchronize_legal
from scripts.sync_service_public import synchronize as synchronize_service_public


async def run_once() -> None:
    """Exécute les deux connecteurs sans bloquer l'API web."""
    await synchronize_service_public()
    try:
        await synchronize_legal()
    except Exception as error:  # noqa: BLE001 - le flux secondaire ne doit pas arrêter le principal.
        print(f"Synchronisation EUR-Lex ignorée : {error}")


async def run_scheduler(interval_seconds: int, once: bool = False) -> None:
    await run_once()
    if once:
        return
    while True:
        await asyncio.sleep(interval_seconds)
        await run_once()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("SYNC_INTERVAL_SECONDS", "86400")),
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_scheduler(args.interval_seconds, once=args.once))
