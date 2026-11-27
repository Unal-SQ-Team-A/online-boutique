#!/usr/bin/env bash
# One command for the cartservice component-level suite (Project Delivery 1).
#   ./run-component-tests.sh            -> baseline + suspected defects + branch coverage
#   ./run-component-tests.sh mutation   -> also runs Stryker.NET on RedisCartStore
# Exit code = verdict of the green baseline (contract tests). Defect tests are reported, not gating.
set -u
cd "$(dirname "$0")"
PROJECT=component-tests/cartservice.componenttests.csproj
RESULTS=component-tests/TestResults
rm -rf "$RESULTS" component-tests/coverage

echo "=== [1/3] Baseline: contract-derived tests (must all pass) ==="
dotnet test "$PROJECT" --filter "Category!=Defect" --logger "console;verbosity=normal"
BASELINE=$?

echo
echo "=== [2/3] Suspected defects: assumed-contract tests (a failure here is a FINDING) ==="
dotnet test "$PROJECT" --filter "Category=Defect" --logger "console;verbosity=normal" --no-build
echo "(defect suite exit code: $? -- non-zero is expected while the defects exist)"

echo
echo "=== [3/3] Branch coverage of the components under test ==="
dotnet test "$PROJECT" --filter "Category!=Defect" --no-build \
  --collect:"XPlat Code Coverage" --results-directory "$RESULTS" > /dev/null
if command -v reportgenerator >/dev/null 2>&1; then
  reportgenerator -reports:"$RESULTS/*/coverage.cobertura.xml" -targetdir:component-tests/coverage \
    -reporttypes:"TextSummary;Html" \
    -classfilters:"+cartservice.cartstore.RedisCartStore;+cartservice.services.CartService;+cartservice.Startup"
  cat component-tests/coverage/Summary.txt
else
  echo "reportgenerator not installed: dotnet tool install -g dotnet-reportgenerator-globaltool"
  echo "raw cobertura files: $RESULTS/*/coverage.cobertura.xml"
fi

if [ "${1:-}" = "mutation" ]; then
  echo
  echo "=== Mutation testing (Stryker.NET) on RedisCartStore ==="
  if ! command -v dotnet-stryker >/dev/null 2>&1; then
    echo "Stryker not installed: dotnet tool install -g dotnet-stryker"
  else
    (cd component-tests && dotnet stryker)
  fi
fi

exit $BASELINE
