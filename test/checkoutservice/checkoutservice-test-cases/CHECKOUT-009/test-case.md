# CHECKOUT-009: cart cleanup and email failures

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Fallan la limpieza del carrito y la notificacion por correo |
| Tecnica | Comportamiento excepcional |
| Entradas | Los doubles de carrito y correo retornan errores |
| Resultado esperado | La orden sigue siendo exitosa y se intenta la confirmacion |
