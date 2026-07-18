import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3

cloudwatch = boto3.client("cloudwatch")
table = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "uptime-checks"))
NAMESPACE = os.environ.get("METRIC_NAMESPACE", "Portfolio/UptimeMonitor")


def check_endpoint(target):
    started = time.perf_counter()
    status, error = 0, None
    try:
        request = urllib.request.Request(target["url"], headers={"User-Agent": "serverless-uptime-monitor/1.0"})
        with urllib.request.urlopen(request, timeout=target.get("timeout", 5)) as response:
            status = response.status
    except (urllib.error.URLError, TimeoutError) as exc:
        error = type(exc).__name__
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    healthy = status == target.get("expected_status", 200) and latency_ms <= target.get("max_latency_ms", 2000)
    return {"name": target["name"], "url": target["url"], "status_code": status, "latency_ms": latency_ms, "healthy": healthy, "error": error}


def record(result):
    now = int(time.time())
    table.put_item(Item={**result, "check_id": f"{result['name']}#{now}", "checked_at": datetime.now(timezone.utc).isoformat(), "expires_at": now + 604800})
    cloudwatch.put_metric_data(Namespace=NAMESPACE, MetricData=[
        {"MetricName": "Availability", "Dimensions": [{"Name": "Service", "Value": result["name"]}], "Value": 1 if result["healthy"] else 0, "Unit": "Count"},
        {"MetricName": "Latency", "Dimensions": [{"Name": "Service", "Value": result["name"]}], "Value": result["latency_ms"], "Unit": "Milliseconds"},
    ])


def lambda_handler(_event, _context):
    targets = json.loads(os.environ.get("TARGETS_JSON", "[]"))
    results = [check_endpoint(target) for target in targets]
    for result in results:
        record(result)
    summary = {"checked": len(results), "healthy": sum(1 for result in results if result["healthy"]), "results": results}
    print(json.dumps(summary))
    return summary
