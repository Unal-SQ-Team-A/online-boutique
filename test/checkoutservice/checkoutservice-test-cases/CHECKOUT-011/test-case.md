# CHECKOUT-011: zero and negative quantities

| Field | Value |
| --- | --- |
| Component | `checkoutService.PlaceOrder` |
| Condition | A cart item has a quantity that does not satisfy `quantity > 0` |
| Technique | Boundary-value analysis at the valid lower bound |
| Inputs | Separate cases with quantity 0 and -1 |
| Expected result | gRPC `InvalidArgument`, no order response, and no payment or shipment |

The rule that quantities must be greater than zero was confirmed for this test set.
No upper quantity limit is specified.
