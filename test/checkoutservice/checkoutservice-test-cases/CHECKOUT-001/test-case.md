# CHECKOUT-001: successful order

| Campo | Valor |
| --- | --- |
| Componente | `checkoutService.PlaceOrder` |
| Condicion | Todas las dependencias funcionan |
| Tecnica | Tabla de decision: camino exitoso |
| Entradas | Carrito con cantidad 2 del producto a 3 USD; envio 2 USD; moneda del usuario USD |
| Resultado esperado | UUID valido, detalles de item y envio, cobro de 8 USD, limpieza del carrito e intento de confirmacion |
