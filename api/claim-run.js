// Vercel Cron entry point. Same logic as claim_bot.py: check the quote,
// claim if anything's owed. No signature/private key involved — see
// README.md for why. Kept as a single file since the whole thing is two
// fetch calls.

export const config = { maxDuration: 30 };

const BASE_URL = "https://harmonicagent.solutions";
const EXPLORER = "https://robinhoodchain.blockscout.com";
const WALLET = "0x819fc86a60a820b7c9ed468cd94cdc719970c0f5";

const HEADERS = {
  "content-type": "application/json",
  origin: BASE_URL,
  referer: `${BASE_URL}/`,
  "user-agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 harmonic-claim-bot-vercel/1.0",
};

export default async function handler(req, res) {
  // Vercel signs cron-triggered requests with this header; if CRON_SECRET
  // is set as a project env var, only accept requests carrying it. Left
  // optional since a stray call here is harmless (idempotent at worst).
  if (process.env.CRON_SECRET) {
    const auth = req.headers["authorization"];
    if (auth !== `Bearer ${process.env.CRON_SECRET}`) {
      return res.status(401).json({ ok: false, reason: "unauthorized" });
    }
  }

  const log = [];
  try {
    const quoteRes = await fetch(`${BASE_URL}/api/claim/quote/${WALLET}`, {
      headers: HEADERS,
    });
    const quote = await quoteRes.json();

    if (!quote.anything) {
      log.push(`nothing claimable yet (totalRounds=${quote.totalRounds ?? 0})`);
      console.log(log.join("\n"));
      return res.status(200).json({ ok: true, log });
    }

    const claimRes = await fetch(`${BASE_URL}/api/claim`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({
        wallet: WALLET,
        ageConfirmed: true,
        riskAcknowledged: true,
        complianceAcknowledged: true,
      }),
    });
    const result = await claimRes.json();
    const sent = result.sent || [];
    const failed = result.failed || [];

    for (const leg of sent) {
      log.push(`claimed ${leg.amount} ${leg.symbol} -> ${EXPLORER}/tx/${leg.txHash}`);
    }
    for (const leg of failed) {
      log.push(`leg failed: ${leg.symbol} (${leg.error})`);
    }
    if (!sent.length && !failed.length) {
      log.push(`claim response: ${result.reason ?? JSON.stringify(result)}`);
    }

    console.log(log.join("\n"));
    return res.status(200).json({ ok: true, log });
  } catch (err) {
    console.error("claim-run error", err);
    return res.status(500).json({ ok: false, error: String(err) });
  }
}
