#!/usr/bin/env python3
"""Auto-claim Harmonic Agent ($HARMONIC) equity rewards.

The claim desk at https://harmonicagent.solutions/#/claim never asks the
wallet to sign or pay gas: the agent's own wallet sends the tokens. The
front end just reads the wallet address and POSTs it to /api/claim. This
script does the same thing directly, on a schedule, with no private key
or RPC access involved.
"""

import argparse
import logging
import random
import re
import time

import requests

BASE_URL = "https://harmonicagent.solutions"
EXPLORER = "https://robinhoodchain.blockscout.com"
WALLET_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

HEADERS = {
    "content-type": "application/json",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 harmonic-claim-bot/1.0",
}


def get_quote(session: requests.Session, wallet: str) -> dict:
    r = session.get(f"{BASE_URL}/api/claim/quote/{wallet}", timeout=15)
    r.raise_for_status()
    return r.json()


def submit_claim(session: requests.Session, wallet: str) -> dict:
    payload = {
        "wallet": wallet,
        "ageConfirmed": True,
        "riskAcknowledged": True,
        "complianceAcknowledged": True,
    }
    r = session.post(f"{BASE_URL}/api/claim", json=payload, timeout=30)
    try:
        return r.json()
    except ValueError:
        return {"ok": False, "reason": f"non-JSON response (HTTP {r.status_code})"}


def run_once(session: requests.Session, wallet: str, log: logging.Logger) -> None:
    quote = get_quote(session, wallet)
    if not quote.get("anything"):
        log.info(
            "nothing claimable yet (totalRounds=%s)", quote.get("totalRounds", 0)
        )
        return

    result = submit_claim(session, wallet)
    sent = result.get("sent") or []
    failed = result.get("failed") or []

    for leg in sent:
        log.info(
            "claimed %s %s -> %s/tx/%s",
            leg.get("amount"),
            leg.get("symbol"),
            EXPLORER,
            leg.get("txHash"),
        )
    for leg in failed:
        log.warning("leg failed: %s (%s)", leg.get("symbol"), leg.get("error"))
    if not sent and not failed:
        log.info("claim response: %s", result.get("reason") or result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wallet", help="Wallet address to claim to (0x... 40 hex chars)")
    parser.add_argument(
        "--once", action="store_true", help="Run a single check-and-claim, then exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help=(
            "Seconds between attempts when not using --once (default 3600 = hourly; "
            "rounds stay claimable for 24h and 144 stack up, so hourly claims exactly "
            "as much as any tighter interval, per the site's own claim desk)"
        ),
    )
    parser.add_argument("--log-file", default=None, help="Also write logs to this file")
    args = parser.parse_args()

    if not WALLET_RE.match(args.wallet):
        parser.error("wallet must look like 0x followed by 40 hex characters")

    handlers = [logging.StreamHandler()]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers
    )
    log = logging.getLogger("harmonic-claim")

    session = requests.Session()
    session.headers.update(HEADERS)
    wallet = args.wallet.lower()

    if args.once:
        try:
            run_once(session, wallet, log)
        except requests.RequestException as e:
            log.error("request failed: %s", e)
        return

    log.info("starting claim loop for %s every ~%ss", wallet, args.interval)
    while True:
        try:
            run_once(session, wallet, log)
        except requests.RequestException as e:
            log.error("request failed: %s", e)
        except Exception:
            log.exception("unexpected error")
        time.sleep(max(30, args.interval + random.uniform(-5, 5)))


if __name__ == "__main__":
    main()
