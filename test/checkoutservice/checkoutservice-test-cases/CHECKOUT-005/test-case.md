# CHECKOUT-005: item currency conversion failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo al convertir el precio del item |
| Tecnica | Comportamiento excepcional |
| Entradas | El double de moneda falla en la primera conversion |
| Resultado esperado | Error gRPC `Internal`; sin respuesta de orden |
