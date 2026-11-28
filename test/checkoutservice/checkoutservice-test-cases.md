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
| CHECKOUT-010 | [minimum positive quantity](checkoutservice-test-cases/CHECKOUT-010/test-case.md) |
| CHECKOUT-011 | [zero and negative quantities](checkoutservice-test-cases/CHECKOUT-011/test-case.md) |

The doubles implement the cart, catalog, currency, shipping, payment, and email gRPC
services over an in-process `bufconn` listener. They replace all external services;
no external network or database is used. The order UUID is generated dynamically
and checked for valid syntax. Each test creates a fresh fixture.

The checkout rule is that every item quantity must be greater than zero. CHECKOUT-010
tests the minimum valid quantity 1; CHECKOUT-001 tests the adjacent value 2.
CHECKOUT-011 tests the invalid boundary values 0 and -1 and expects gRPC
`InvalidArgument`. No upper quantity limit is specified.

The checkoutservice README only documents dependency restoration. The product
requirements describe the user journey but not checkout error or pricing rules.
The `quantity > 0` rule was confirmed by the user and is covered by CHECKOUT-010 and
CHECKOUT-011. Other behavior without an independent requirement is derived from
`main.go` and the protobuf contract and remains a code-based assumption. The generated
order UUID is checked for valid syntax rather than an exact value.

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
