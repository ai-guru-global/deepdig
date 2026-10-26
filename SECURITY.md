# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | yes       |

## Reporting a vulnerability

We take security seriously, especially because DeepDig handles API keys and
sits between your IDE and external services.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use GitHub's [private vulnerability reporting]
(https://github.com/ai-guru-global/deepdig/security/advisories/new), or email
**allengaller@qq.com** with:

- A description of the issue and its impact
- Steps to reproduce or a proof of concept
- Affected version/commit

You can expect an initial response within 72 hours. We will credit reporters
in the release notes unless they prefer to remain anonymous.

## Security model notes

- API keys are read from local environment variables / `.env` only; they are
  never placed into prompts, logs, or tool output.
- In gateway mode, set `DEEPDIG_ACCESS_TOKEN` to require bearer-token
  authentication; an open gateway will print a warning at startup.
- Outbound requests go exclusively to the configured provider endpoints
  (DashScope / Zhipu / Moonshot). No telemetry is collected.
