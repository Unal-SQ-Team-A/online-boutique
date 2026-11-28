# CHECKOUT-007: payment failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo el pago |
| Tecnica | Comportamiento excepcional |
| Entradas | El double de pago retorna un error |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
