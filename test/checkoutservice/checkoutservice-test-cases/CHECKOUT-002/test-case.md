# CHECKOUT-002: cart retrieval failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo al recuperar el carrito |
| Tecnica | Comportamiento excepcional |
| Entradas | El double del carrito retorna un error |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
