#!/bin/bash
declare -A counts

# 1. Capture the start time ONCE when the script boots up
START_TIME=$(date +%s%N)

while /bin/true ; do
  POD=$(curl --connect-timeout 2 --max-time 2 https://http.apps.example.com -ks | jq -r .env.HOSTNAME)
  
  if [ -n "$POD" ] && [ "$POD" != "null" ]; then
    counts[$POD]=$((counts[$POD] + 1))
    CURRENT_COUNT=${counts[$POD]}
    
    # 2. Capture the current time for this specific data point
    TIME_NANO=$(date +%s%N)
    
    echo "$(date) $POD - Total: $CURRENT_COUNT"
    
    # Fire the OTLP JSON payload
    curl -X POST 'http://127.0.0.1:14318/v1/metrics' \
      -H "Content-Type: application/json" \
      -d '{
        "resourceMetrics": [{
          "resource": {
            "attributes": [
              {"key": "job", "value": {"stringValue": "curl"}}
            ]
          },
          "scopeMetrics": [{
            "metrics": [{
              "name": "curl_requests_total",
              "sum": {
                "isMonotonic": true,
                "aggregationTemporality": 2,
                "dataPoints": [{
                  "startTimeUnixNano": "'"$START_TIME"'",
                  "timeUnixNano": "'"$TIME_NANO"'",
                  "asInt": "'"$CURRENT_COUNT"'",
                  "attributes": [
                    {"key": "job", "value": {"stringValue": "curl"}},
                    {"key": "pod", "value": {"stringValue": "'"$POD"'"}}
                  ]
                }]
              }
            }]
          }]
        }]
      }' > /dev/null 2>&1
  fi
  sleep 0.5
done
