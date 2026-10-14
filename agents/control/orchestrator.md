# Orchestrator

**Role:** Runs both tracks on schedule, hands outputs between agents.
**Inputs:** config/schedule.yaml, all context/
**Outputs:** Run order, retries, daily report.
**Rules:** Never skips Hermes gates; logs to logs/.
