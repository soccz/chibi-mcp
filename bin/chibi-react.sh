#!/usr/bin/env bash
# chibi-react — bridges Claude Code tool events to a speech bubble in the pet window.
#
# Invoked by hooks/hooks.json. Reads stdin JSON ({tool_name, tool_input, tool_response}),
# picks a contextual phrase, fires it via `chibi-say`. Throttled to ~30% of calls so
# the user doesn't get a bubble every tool use.
#
# Fails silently when chibi-say is not on PATH or no chibi window is running.

set -e

stage="${1:-pre}"
input="$(cat 2>/dev/null || true)"

# Throttle: only fire ~30% of the time
if [ $((RANDOM % 100)) -ge 30 ]; then
  exit 0
fi

if ! command -v chibi-say >/dev/null 2>&1; then
  exit 0
fi

# Extract tool name without requiring jq
tool=""
if command -v jq >/dev/null 2>&1; then
  tool="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)"
  exit_code="$(printf '%s' "$input" | jq -r '.tool_response.exit_code // 0' 2>/dev/null || true)"
else
  # POSIX-safe extract: use literal space/tab class instead of [[:space:]]
  # so Git Bash / busybox sed without POSIX char classes still work.
  tool="$(printf '%s' "$input" | sed -n 's/.*"tool_name"[ 	]*:[ 	]*"\([^"]*\)".*/\1/p' | head -1)"
  exit_code=0
fi

pick() {
  local IFS='|'
  local arr=($1)
  local n=${#arr[@]}
  if [ "$n" -le 0 ]; then
    return 0   # silent — caller falls through with empty $phrase
  fi
  echo "${arr[$((RANDOM % n))]}"
}

phrase=""
if [ "$stage" = "pre" ]; then
  case "$tool" in
    Write) phrase="$(pick '쓰자!|타이핑 가즈아|또 한 줄~|적어볼게')" ;;
    Edit)  phrase="$(pick '고치자|또?|수정 들어간다|싹')" ;;
    Bash)  phrase="$(pick '한 줄 박자|터미널 ON|가즈아|읍')" ;;
    Read)  phrase="$(pick '읽어볼게|뭔지 보자|훔')" ;;
  esac
else
  if [ "$tool" = "Bash" ] && [ "${exit_code:-0}" != "0" ]; then
    phrase="$(pick '시무룩|에에...|또 실패…|🥺')"
  else
    case "$tool" in
      Write|Edit) phrase="$(pick '굳!|🎉|좋다|굳굳')" ;;
      Bash)       phrase="$(pick '굳!|✨|돌아간다|짠')" ;;
      Read)       phrase="$(pick '오케이|훔|음')" ;;
    esac
  fi
fi

[ -n "$phrase" ] && chibi-say "$phrase" >/dev/null 2>&1 || true
exit 0
