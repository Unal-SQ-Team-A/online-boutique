# Checkout service component test cases

Los casos estan separados para que cada prueba sea independiente. El identificador
aparece en el nombre de la prueba Go y se imprime con `go test -v`.

| ID | Caso independiente |
| --- | --- |
| CHECKOUT-001 | [successful order](checkoutservice-test-cases/CHECKOUT-001/test-case.md) |
| CHECKOUT-002 | [cart retrieval failure](checkoutservice-test-cases/CHECKOUT-002/test-case.md) |
| CHECKOUT-003 | [product lookup failure](checkoutservice-test-cases/CHECKOUT-003/test-case.md) |
| CHECKOUT-004 | [shipping quote failure](checkoutservice-test-cases/CHECKOUT-004/test-case.md) |
| CHECKOUT-005 | [item currency conversion failure](checkoutservice-test-cases/CHECKOUT-005/test-case.md) |
| CHECKOUT-006 | [shipping currency conversion failure](checkoutservice-test-cases/CHECKOUT-006/test-case.md) |
| CHECKOUT-007 | [payment failure](checkoutservice-test-cases/CHECKOUT-007/test-case.md) |
| CHECKOUT-008 | [shipment failure](checkoutservice-test-cases/CHECKOUT-008/test-case.md) |
| CHECKOUT-009 | [cart cleanup and email failures](checkoutservice-test-cases/CHECKOUT-009/test-case.md) |

The doubles implement the cart, catalog, currency, shipping, payment, and email gRPC
services over an in-process `bufconn` listener. They replace all external services;
no network, database, or clock is used. Each test creates a fresh fixture.

The checkoutservice README only documents dependency restoration. The product
requirements describe the user journey but not checkout error or pricing rules.
Therefore, behavior tested here is derived from `main.go` and the protobuf contract;
those behaviors are code-based assumptions until confirmed by business documentation.
The generated order UUID is checked for valid syntax rather than an exact value.

Run the suite from Docker Compose with:

```powershell
docker compose -f test\compose.yaml run --rm checkoutservice-tests
```

Run mutation testing with:

```powershell
docker compose -f test\compose.yaml run --rm checkoutservice-mutation
```

The Go toolchain reports statement coverage; it does not natively report branch
coverage. Do not present its coverage percentage as branch coverage.
