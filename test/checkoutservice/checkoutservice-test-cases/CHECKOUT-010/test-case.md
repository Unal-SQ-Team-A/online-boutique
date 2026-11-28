# CHECKOUT-010: minimum positive quantity

| Field | Value |
| --- | --- |
| Component | `checkoutService.PlaceOrder` |
| Condition | The cart contains the minimum valid quantity under the rule `quantity > 0` |
| Technique | Boundary-value analysis; compare quantity 1 with adjacent quantity 2 in CHECKOUT-001 |
| Inputs | Quantity 1 of `product-1` at 3 USD; shipping 2 USD; user currency USD |
| Expected result | Successful order with quantity 1, item cost 3 USD, and charge of 5 USD |

The checkout rule `quantity > 0` was confirmed for this test set. No upper quantity
limit is specified.
