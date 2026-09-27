# harmonic_claim_bot

Automates claiming $HARMONIC holder equity rewards from
https://harmonicagent.solutions/#/claim, on a schedule, via Vercel Cron.

No private key or wallet signature is involved: the site's own claim
mechanism sends tokens from the agent's wallet to yours and pays the gas
itself. This just does the same HTTP calls the "Claim my equities" button
does — `GET /api/claim/quote/{wallet}` then `POST /api/claim` with your
wallet address.

Rounds stay claimable for 24h and 144 stack up (per `/api/claim/clock` and
confirmed by the site's own claim desk), so hourly claims collect exactly
as much as a tighter interval — there's no benefit to polling more often.

## Run on a schedule via Vercel Cron (recommended, live)

`api/claim-run.js` is a small serverless function with the same logic as
`claim_bot.py`; `vercel.json` schedules it hourly on the hour
(`cron: "0 * * * *"`). Deployed at
https://harmonicclaimbot.vercel.app — pushing to `main` redeploys
automatically (the Vercel project is linked to this GitHub repo).

Trigger it manually to test:

```bash
curl https://harmonicclaimbot.vercel.app/api/claim-run
```

Check run history/logs in the Vercel dashboard → project →
Deployments/Logs, or Cron Jobs under project settings.

We tried GitHub Actions' `schedule` trigger first — it's explicitly
documented by GitHub as best-effort with no SLA, and drifted by up to ~6
hours in practice (still harmless given the 24h claim window, but not
what "hourly" was supposed to mean). Vercel Cron is a first-party
scheduling primitive and runs much closer to on-time.

## Manual test (same logic, run locally)

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

## Alternative: macOS launchd (local-only, not in use)

`com.harmonicclaim.bot.plist` runs the same thing as a local LaunchAgent —
useful for ad-hoc testing, but only fires while this specific Mac is
awake and logged in (misses runs during sleep, which is what led us to
move scheduling server-side in the first place). Currently unloaded.

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
