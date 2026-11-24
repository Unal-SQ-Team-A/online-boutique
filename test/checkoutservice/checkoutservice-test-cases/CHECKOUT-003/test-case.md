# CHECKOUT-003: product lookup failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo al consultar el producto |
| Tecnica | Comportamiento excepcional |
| Entradas | El double del catalogo retorna un error |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
