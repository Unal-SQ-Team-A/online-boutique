# Verificación a nivel de componente: CheckoutService

## Equipo

- Equipo: por completar según la asignación del grupo.
- Integrantes: por completar.

## Software System

- **Nombre:** Online Boutique.
- **Descripción:** demo de comercio electrónico basada en microservicios. El componente seleccionado implementa el flujo de creación de una orden de compra.
- **Arquitectura:** microservicios escritos principalmente en Go; el checkout expone RPC gRPC y se comunica con Cart, Product Catalog, Currency, Shipping, Payment y Email.
- **Tecnologías:** Go, gRPC, Protobuf, Docker Compose y GitHub Actions.
- **Componente bajo prueba:** `checkoutService.PlaceOrder`.
- **Repositorio:** [nferrucho-unal/boutique](https://github.com/nferrucho-unal/boutique).
- **Versión probada:** rama o commit bajo revisión en el entorno local.
- **Tipo de entrega:** prueba piloto inicial. El objetivo es validar que las pruebas sean independientes, sencillas de ejecutar y útiles para detectar fallos principales, sin ampliar todavía el alcance a cargas, concurrencia, integración real o pruebas exhaustivas.

## Alcance de la prueba piloto

Las nueve pruebas actuales son adecuadas para una primera ejecución porque:

- utilizan un único dato positivo de 2 unidades y precios pequeños;
- reemplazan todas las dependencias externas con dobles locales;
- no usan base de datos, reloj, red externa ni datos aleatorios;
- verifican resultados visibles como códigos gRPC, UUID, importe y intentos de operaciones;
- requieren solo Go, Docker Compose y GitHub Actions;
- pueden ejecutarse repetidamente con un comando de una sola suite.

Las pruebas no pretenden demostrar exhaustividad. Se excluyen de esta fase límites de cantidades, monedas adicionales, desbordamiento, múltiples productos, latencia, reintentos y servicios reales.

La complejidad aceptable es deliberadamente baja: el fixture comparte una estructura mínima y cada caso modifica solamente un comportamiento del doble antes de invocar `PlaceOrder`.

## Contratos

Para esta prueba piloto se documenta el contrato observable mínimo necesario para los casos realizados. Las afirmaciones derivadas exclusivamente de `main.go` o del contrato generado se identifican como asunciones.

### Precondiciones

| ID | Precondición | Fuente |
| --- | --- | --- |
| PRE-001 | `PlaceOrder` recibe un `PlaceOrderRequest` válido con identificador de usuario, moneda, dirección, correo y datos de tarjeta. | Protobuf / código. |
| PRE-002 | Las dependencias tienen una respuesta positiva o un único fallo controlado por el doble correspondiente. | Diseño de las pruebas piloto. |

### Postcondiciones

| ID | Postcondición | Fuente |
| --- | --- | --- |
| POST-001 | Si todas las operaciones críticas tienen éxito, se retorna una `PlaceOrderResponse` con UUID válido, coste de envío localizado, dirección, artículos y ID de seguimiento. | Código de `PlaceOrder` y comprobaciones de CHECKOUT-001. |
| POST-002 | En el caso positivo, el cobro corresponde al importe de 8 USD esperado. | Código de cálculo de total y comprobación CHECKOUT-001; no existe una especificación independiente completa. |
| POST-003 | Después de un cobro exitoso se intenta el envío y después se intenta vaciar el carrito. | Código de `PlaceOrder`. |
| POST-004 | Un fallo temprano o intermedio produce `codes.Internal` y una respuesta nula. | Comportamiento implementado en `main.go`. |
| POST-005 | Un fallo de ShipOrder produce `codes.Unavailable` y una respuesta nula. | Comportamiento implementado en `main.go`. |
| POST-006 | Los fallos al vaciar el carrito o enviar el correo no invalidan una orden ya creada. | Comportamiento implementado en `main.go`; confirmado por CHECKOUT-009. |

### Invariantes

- `PlaceOrder` no retorna una respuesta junto con un error crítico.
- La respuesta exitosa contiene un `OrderId` con sintaxis UUID válida; no se exige una cadena UUID exacta.
- Las operaciones críticas se realizan antes de considerar exitosa la orden.
- El intento de vaciar el carrito no se propaga como error fatal.
- El intento de enviar la confirmación no se propaga como error fatal.
- Cada prueba utiliza una instancia nueva de los dobles y del servidor gRPC en memoria.

Los límites de cantidades, cantidades negativas o cero, desbordamiento, monedas adicionales y estados vacíos quedan fuera de esta prueba piloto porque no están definidos por la documentación disponible.

### Comportamiento excepcional

| Condición excepcional | Resultado esperado |
| --- | --- |
| Fallo al generar el UUID | `Internal`, sin respuesta. |
| Fallo al recuperar el carrito | `Internal`, sin respuesta. |
| Fallo al consultar el catálogo | `Internal`, sin respuesta. |
| Fallo al cotizar el envío | `Internal`, sin respuesta. |
| Fallo al convertir el precio del artículo | `Internal`, sin respuesta. |
| Fallo al convertir el coste de envío | `Internal`, sin respuesta. |
| Fallo al cobrar | `Internal`, sin respuesta. |
| Fallo al enviar | `Unavailable`, sin respuesta. |
| Fallo al limpiar el carrito o al enviar el correo | Orden exitosa; la confirmación se intenta. |

El único comportamiento validado en la suite sobre fallos fue los casos CHECKOUT-002 a CHECKOUT-009. El fallo al generar UUID no tiene caso explícito en la suite actual.

## Diseño de Pruebas

### Matriz formalizada

| ID | Componente | Condición | Técnica | Entradas | Resultado esperado |
| --- | --- | --- | --- | --- | --- |
| CHECKOUT-001 | `checkoutService.PlaceOrder` | Todas las dependencias críticas tienen éxito | Tabla de decisión: camino exitoso | Carrito: producto `product-1`, cantidad 2, precio 3 USD. Envío: 2 USD. Moneda: USD. | UUID válido, artículo y envío en la respuesta, cobro 8 USD, limpieza y confirmación intentadas. |
| CHECKOUT-002 | `checkoutService.PlaceOrder` | Recuperación del carrito falla | Comportamiento excepcional | Cart double con `GetCart` fallando. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-003 | `checkoutService.PlaceOrder` | Consulta de producto falla | Comportamiento excepcional | Catalog double con `GetProduct` fallando. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-004 | `checkoutService.PlaceOrder` | Cotización de envío falla | Comportamiento excepcional | Shipping double con `GetQuote` fallando. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-005 | `checkoutService.PlaceOrder` | Conversión del precio del artículo falla | Comportamiento excepcional | Currency double configurado para fallar en la llamada 1. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-006 | `checkoutService.PlaceOrder` | Conversión del precio de envío falla | Comportamiento excepcional | Currency double configurado para fallar en la llamada 2. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-007 | `checkoutService.PlaceOrder` | Pago falla | Comportamiento excepcional | Payment double con `Charge` fallando. | gRPC `Internal`; respuesta nula. |
| CHECKOUT-008 | `checkoutService.PlaceOrder` | Envío falla después del pago | Comportamiento excepcional | Shipping double con `ShipOrder` fallando. | gRPC `Unavailable`; respuesta nula. |
| CHECKOUT-009 | `checkoutService.PlaceOrder` | Limpieza y correo fallan | Comportamiento excepcional no crítico | Cart doble falla al vaciar; Email doble falla al confirmar. | Orden exitosa; intento de correo registrado; no se propaga el error. |

Las especificaciones completas se encuentran en carpetas independientes:

- [Casos CHECKOUT](checkoutservice-test-cases.md)
- [CHECKOUT-001](checkoutservice-test-cases/CHECKOUT-001/test-case.md)
- [CHECKOUT-002](checkoutservice-test-cases/CHECKOUT-002/test-case.md)
- [CHECKOUT-003](checkoutservice-test-cases/CHECKOUT-003/test-case.md)
- [CHECKOUT-004](checkoutservice-test-cases/CHECKOUT-004/test-case.md)
- [CHECKOUT-005](checkoutservice-test-cases/CHECKOUT-005/test-case.md)
- [CHECKOUT-006](checkoutservice-test-cases/CHECKOUT-006/test-case.md)
- [CHECKOUT-007](checkoutservice-test-cases/CHECKOUT-007/test-case.md)
- [CHECKOUT-008](checkoutservice-test-cases/CHECKOUT-008/test-case.md)
- [CHECKOUT-009](checkoutservice-test-cases/CHECKOUT-009/test-case.md)

## Aislamiento

### Dobles de prueba

| Dependencia | Doble utilizado | Tipo | Control realizado |
| --- | --- | --- | --- |
| Cart | `checkoutCartDouble` | Stub/spy simple | Retorna un artículo fijo o falla una operación. |
| Product Catalog | `checkoutProductDouble` | Stub simple | Retorna un producto fijo o falla la consulta. |
| Currency | `checkoutCurrencyDouble` | Stub con contador básico | Convierte sin cambio en el caso positivo y falla en la primera o segunda llamada. |
| Shipping | `checkoutShippingDouble` | Stub/spy simple | Retorna cotización y seguimiento fijos o falla una operación. |
| Payment | `checkoutPaymentDouble` | Stub/spy simple | Retorna una transacción fija o falla el cobro. |
| Email | `checkoutEmailDouble` | Spy/stub simple | Registra el intento y puede fallar. |
| Servidor gRPC externo | `bufconn` | Servidor gRPC local | Evita servicios reales y conexiones de red externas. |

### Control de no-determinismo

- Cada caso crea una fixture nueva mediante `newCheckoutTestService`.
- Los dobles no usan reloj ni acceso a base de datos.
- Los datos de carrito, catálogo, precios, envío y tarjeta son deterministas.
- El UUID generado no se compara por valor: solo se valida su sintaxis.
- Los identificadores de usuario, transacción y seguimiento son fijos.
- El servidor y sus conexiones se cierran con `t.Cleanup`.
- No hay ejecución paralela de los casos ni dependencias en el orden de ejecución.

### Supuestos de los dobles

- El double de Currency conserva moneda y nanos al convertir; en el caso positivo esto permite calcular 8 USD.
- El double de Catalog conoce únicamente `product-1`.
- El double de Cart devuelve exactamente un artículo por defecto.
- Los datos de tarjeta son representaciones ficticias y no representan integración real de pago.
- Los dobles asumen que las respuestas gRPC correctas pueden representarse con estructuras Protobuf.
- Los fallos simulados representan errores RPC visibles al componente, no errores de transporte o red reales.

## Implementación y Ejecución

### Herramientas

- **Lenguaje y framework:** Go 1.27 y paquete `testing`.
- **Pruebas aisladas:** dobles gRPC sencillos registrados sobre `bufconn`.
- **Cobertura:** reporte básico generado por Go como evidencia de ejecución.
- **Pruebas pesadas:** las pruebas de mutación están disponibles, pero no son necesarias para aprobar la piloto inicial.
- **Ejecución reproducible:** un servicio de Docker Compose.
- **Automatización:** GitHub Actions puede ejecutar la suite piloto automáticamente.

### Ejecución unificada

```powershell
docker compose -f test/compose.yaml run --rm checkoutservice-tests
```

La suite normal de Go ya fue ejecutada por Docker Compose y finalizó correctamente según la ejecución confirmada. Los IDs aparecen en las pruebas Go mediante subtests y en el resultado de `go test -v`.

### Evidencia de veredictos

| Suite | Resultado |
| --- | --- |
| CHECKOUT-001 a CHECKOUT-009 | Confirmado `PASS` por la ejecución exitosa de `checkoutservice-tests`. |
| Cobertura básica | El reporte se genera en `test/checkoutservice/checkoutservice-coverage.out`; se usa como evidencia complementaria, no como porcentaje final de decisiones. |
| Mutation testing | Diferido para una fase posterior porque no es necesario para validar el piloto inicial. |
| GitHub Actions | El workflow escucha `push`, `pull_request` y ejecución manual y puede ejecutar la suite normal. |

## Adecuación

### Cobertura de ramas

Para una prueba piloto, la cobertura se considera suficiente si el conjunto demuestra el camino positivo, los principales fallos críticos y los dos fallos no críticos. El toolchain de Go reporta **statement coverage**, no branch coverage; por eso no se presenta el porcentaje como cobertura de decisiones o ramas.

La suite contiene caminos positivos y excepcionales que ejecutan:

- Camino exitoso completo.
- Fallos tempranos: Cart y Catalog.
- Fallos intermedios: cotización y conversiones.
- Fallos posteriores: Payment y Shipment.
- Camino no fatal: fallos de EmptyCart y Email.

La cobertura extendida de casos adicionales queda fuera del piloto:

- Fallo al generar UUID, ya que `uuid.NewUUID()` no tiene doble.
- Carrito vacío o sin artículos.
- Varias cantidades o conversión a monedas distintas de USD.
- Conversión que recibe nanos.
- Respuesta nula de dependencias.
- Carrito con varios productos.
- Validación de campos no definidos por el contrato.

El criterio para cerrar esta fase es tener los nueve casos en estado PASS y conservar el reporte generado por la ejecución. Si se agregan casos posteriores, conviene conservar también la fecha o identificador de ejecución.

### Mutation testing

El servicio dispone de una configuración de pruebas de mutación con Gremlins, pero no forma parte de la aprobación del piloto inicial. Ejecutarla ahora añadiría costo y complejidad sin aportar una primera señal distinta a los nueve veredictos actuales.

Cuando el piloto sea aprobado, la mutación puede usarse para fortalecer casos concretos. En esa fase posterior deben registrarse el número de mutantes, los mutantes asesinados y supervivientes, los mutantes equivalentes y el mutation score.

## Hallazgos

### Defectos encontrados

No se detectó una diferencia entre el resultado esperado y el observado en los nueve casos ejecutados: el comportamiento coincide con las aserciones implementadas.

Es posible que la ausencia de defectos sea resultado de que los casos se derivaron principalmente del código y no de reglas independientes de negocio.

Para el alcance piloto esto se considera un resultado positivo: las pruebas son capaces de ejecutar el flujo exitoso y los principales fallos sin requerir infraestructura externa.

### Inconsistencias de la especificación

La documentación disponible no describe los siguientes contratos:

- Límites válidos de cantidad.
- Comportamiento para cantidades cero o negativas.
- Comportamiento ante desbordamiento del total.
- Monedas soportadas.
- Reglas exactas de conversión y redondeo.
- Mensajes detallados de errores gRPC.
- Comportamiento si el UUID no puede generarse.
- Comportamiento si el carrito está vacío.
- Comportamiento si una respuesta del servicio llega nula.

Por esta razón, los casos existentes son código-based assumptions y deben confirmarse con el dueño del producto o documentación de negocio.

### Componentes difíciles de probar

| Componente o condición | Dificultad | Justificación |
| --- | --- | --- |
| `PlaceOrder` | Coordinación moderada | Ejecuta varios servicios secuencialmente, aunque el piloto usa una sola configuración y valores pequeños. |
| Conversión de Currency | Control básico de llamadas | El caso necesita distinguir la primera y segunda conversión, pero el contador del double es sencillo. |
| Generación de UUID | Fuera del piloto | `uuid.NewUUID()` se ejecuta internamente y no existe un doble configurado. |
| EmptyCart y Email | Verificación sencilla del intento | Los errores no son fatales; basta comprobar que la orden existe y que el correo fue intentado. |
| Multiplicación y suma monetaria | Expansión posterior | Límites, nanos y monedas adicionales requieren reglas independientes y no son necesarias en el piloto. |

## Conclusión del piloto

Las pruebas realizadas son suficientemente sencillas y adecuadas para una primera fase: son independientes, usan datos mínimos, reemplazan dependencias con dobles locales y producen nueve veredictos claros. Deben aprobarse como prueba piloto antes de invertir en mutación, matrices de límites o integración con servicios reales.

## Archivos relevantes

- Implementación: [main.go](../src/checkoutservice/main.go)
- Pruebas: [main_test.go](main_test.go)
- Índice de casos: [checkoutservice-test-cases.md](checkoutservice-test-cases.md)
- Compose: [compose.yaml](compose.yaml)
- Workflow: [checkoutservice-quality.yml](../.github/workflows/checkoutservice-quality.yml)
