# harmonic_claim_bot

Automates claiming $HARMONIC holder equity rewards from
https://harmonicagent.solutions/#/claim, on a schedule, via GitHub Actions.

No private key or wallet signature is involved: the site's own claim
mechanism sends tokens from the agent's wallet to yours and pays the gas
itself. This script just does the same HTTP call the "Claim my equities"
button does — `POST /api/claim` with your wallet address.

Rounds stay claimable for 24h and 144 stack up (per `/api/claim/clock` and
confirmed by the site's own claim desk), so hourly claims collect exactly
as much as a tighter interval — there's no benefit to polling more often.

## Run on a schedule via GitHub Actions (recommended)

`.github/workflows/claim.yml` runs `claim_bot.py --once` every hour
(`cron: "0 * * * *"`) plus supports manual runs via the "Run workflow"
button on the Actions tab. Nothing to configure — no secrets needed since
the wallet address isn't sensitive. Once this repo is pushed to GitHub,
it starts running on its own; check the Actions tab for run history/logs.

Free tier: each run takes a few seconds, well within GitHub's free CI
minutes even on a private repo.

## Manual test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
python3 claim_bot.py 0x819fc86a60a820b7c9ed468cd94cdc719970c0f5 --once
```

This is a real request — if anything is claimable it will actually claim
it. Output looks like:

```
2026-09-26 18:03:11 INFO nothing claimable yet (totalRounds=12)
```

or, when there's something to claim:

```
2026-09-26 18:03:11 INFO claimed 0.011 AAPL -> https://robinhoodchain.blockscout.com/tx/0x...
```

## Alternative: macOS launchd (local-only)

`com.harmonicclaim.bot.plist` runs the same thing as a local LaunchAgent —
useful for testing, but only fires while this specific Mac is awake and
logged in (misses runs during sleep). GitHub Actions above doesn't have
that limitation. To use it instead of/alongside GitHub Actions:

```bash
cp com.harmonicclaim.bot.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.harmonicclaim.bot.plist
launchctl list | grep harmonicclaim   # confirm it's loaded
tail -f claim.log
```

Stop it with:

```bash
launchctl unload -w ~/Library/LaunchAgents/com.harmonicclaim.bot.plist
```
