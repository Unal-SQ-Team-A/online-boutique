# CHECKOUT-004: shipping quote failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo al solicitar la cotizacion de envio |
| Tecnica | Comportamiento excepcional |
| Entradas | El double de envio retorna un error en la cotizacion |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
