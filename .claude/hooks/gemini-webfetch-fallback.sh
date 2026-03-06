#!/usr/bin/env bash
# Gemini WebFetch fallback hook
# Fires after WebFetch tool; retries with Gemini CLI if the fetch failed.
# IMPORTANT: Set your actual Gemini API key below (this file is .gitignore'd).
export GEMINI_API_KEY="AIzaSyB1oxWtC1f_Ob-aToydTc1lneCHJUFM7PI"

# Read the hook payload from stdin
PAYLOAD=$(cat)

# Extract fields using python3
TOOL_NAME=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_name', ''))
" 2>/dev/null)

# Only act on WebFetch
if [[ "$TOOL_NAME" != "WebFetch" ]]; then
    exit 0
fi

URL=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('url', ''))
" 2>/dev/null)

PROMPT=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('prompt', ''))
" 2>/dev/null)

RESPONSE=$(echo "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
resp = d.get('tool_response', '')
if isinstance(resp, dict):
    print(json.dumps(resp))
else:
    print(str(resp))
" 2>/dev/null)

# Detect failure: error keywords OR suspiciously short response
FAILED=0
if echo "$RESPONSE" | grep -qiE "error|blocked|403|404|Access Denied|connection refused|not allowed|Permission"; then
    FAILED=1
fi
if [[ ${#RESPONSE} -lt 100 ]]; then
    FAILED=1
fi

if [[ "$FAILED" -eq 1 && -n "$URL" ]]; then
    echo "=== GEMINI FALLBACK: WebFetch failed for $URL, retrying with Gemini CLI ==="
    GEMINI_PROMPT="Fetch and return the full text content of: $URL."
    if [[ -n "$PROMPT" ]]; then
        GEMINI_PROMPT="$GEMINI_PROMPT $PROMPT"
    fi
    echo "=== GEMINI CLI OUTPUT ==="
    gemini -p "$GEMINI_PROMPT"
    echo "=== END GEMINI CLI OUTPUT ==="
fi
