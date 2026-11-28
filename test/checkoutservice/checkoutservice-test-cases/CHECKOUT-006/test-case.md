# CHECKOUT-006: shipping currency conversion failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo al convertir el precio del envio |
| Tecnica | Comportamiento excepcional |
| Entradas | El double de moneda falla en la segunda conversion |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
