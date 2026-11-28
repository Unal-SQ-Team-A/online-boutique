#!/usr/bin/env bash
# Runs the repository's tests grouped by type.
#
#   scripts/run-tests.sh [type ...]
#
# Types:
#   dotnet    cartservice: contract baseline (component-tests) + service tests
#   defects   cartservice: suspected-defect suite (failures are findings, not gating)
#   go        frontend, shippingservice, productcatalogservice, checkoutservice/money (+ checkoutservice via docker)
#   node      paymentservice, currencyservice
#   python    recommendationservice
#   mutation  Stryker.NET (cartservice) -- slow, only when requested
#   all       dotnet defects go node python   (default; mutation excluded)
#
# Missing toolchains are reported as SKIPPED. Exit code != 0 if any gating type FAILED.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.local/go/bin"

declare -a SUMMARY
FAILED=0

record() { SUMMARY+=("$(printf '%-10s %-8s %s' "$1" "$2" "$3")"); [ "$2" = "FAILED" ] && FAILED=1; return 0; }
need()   { command -v "$1" >/dev/null 2>&1; }

run_step() { # type label cmd...
  local type="$1" label="$2"; shift 2
  echo; echo "--- [$type] $label"
  if "$@"; then record "$type" PASSED "$label"; else record "$type" FAILED "$label"; fi
}

t_dotnet() {
  if ! need dotnet; then record dotnet SKIPPED "dotnet not installed"; return; fi
  run_step dotnet "cartservice component tests (baseline)" \
    dotnet test src/cartservice/component-tests/cartservice.componenttests.csproj --filter "Category!=Defect"
  [ -f src/cartservice/tests/cartservice.tests.csproj ] && run_step dotnet "cartservice service tests" \
    dotnet test src/cartservice/tests/cartservice.tests.csproj
}

t_defects() {
  if ! need dotnet; then record defects SKIPPED "dotnet not installed"; return; fi
  echo; echo "--- [defects] cartservice suspected defects (non-gating)"
  if dotnet test src/cartservice/component-tests/cartservice.componenttests.csproj --filter "Category=Defect"; then
    record defects PASSED "no defect reproduced"
  else
    record defects FINDINGS "defects reproduced (expected while they exist)"
  fi
}

t_go() {
  if need go; then
    for d in src/frontend src/shippingservice src/productcatalogservice src/checkoutservice/money; do
      run_step go "$d" bash -c "cd '$d' && go test ./..."
    done
  else
    record go SKIPPED "go not installed (frontend/shipping/productcatalog/money)"
  fi
  # checkoutservice tests are injected through a go overlay with /workspace paths -> run in the container
  if need docker; then
    run_step go "checkoutservice (docker)" docker compose -f test/compose.yaml run --rm checkoutservice-tests
  else
    record go SKIPPED "docker not installed (checkoutservice)"
  fi
}

t_node() {
  if ! need npm; then record node SKIPPED "npm not installed"; return; fi
  for d in src/paymentservice src/currencyservice; do
    [ -d "$d/node_modules" ] || (cd "$d" && npm ci --silent)
    run_step node "$d" bash -c "cd '$d' && npm test"
  done
}

t_python() {
  if ! need python3; then record python SKIPPED "python3 not installed"; return; fi
  local venv="$ROOT/.venv-tests"
  if [ ! -d "$venv" ]; then
    python3 -m venv "$venv" && "$venv/bin/pip" install -q -r src/recommendationservice/requirements.txt pytest \
      || { record python FAILED "could not install recommendationservice dependencies"; return; }
  fi
  run_step python "recommendationservice" \
    bash -c "cd src/recommendationservice && '$venv/bin/python' -m pytest tests -q"
}

t_mutation() {
  if ! need dotnet-stryker; then record mutation SKIPPED "dotnet tool install -g dotnet-stryker"; return; fi
  run_step mutation "Stryker.NET on RedisCartStore" bash -c "cd src/cartservice/component-tests && dotnet stryker"
}

TYPES=("$@")
[ ${#TYPES[@]} -eq 0 ] && TYPES=(all)
for t in "${TYPES[@]}"; do
  case "$t" in
    all) for x in dotnet defects go node python; do "t_$x"; done ;;
    dotnet|defects|go|node|python|mutation) "t_$t" ;;
    *) echo "Unknown type: $t (dotnet|defects|go|node|python|mutation|all)"; exit 2 ;;
  esac
done

echo; echo "================ SUMMARY ================"
printf '%s\n' "${SUMMARY[@]}"
exit $FAILED
