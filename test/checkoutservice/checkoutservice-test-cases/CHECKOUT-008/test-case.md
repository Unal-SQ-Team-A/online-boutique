# CHECKOUT-008: shipment failure

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallo el envio despues del pago |
| Tecnica | Comportamiento excepcional |
| Entradas | El double de envio retorna un error al crear el envio |
| Resultado esperado | Error gRPC `Unavailable`; sin respuesta de orden |
