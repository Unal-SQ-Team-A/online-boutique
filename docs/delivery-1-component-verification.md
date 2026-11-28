# Entregable 1 — Verificación a nivel de componente (`team-A-p1`)

**Sistema:** Online Boutique (`Unal-SQ-Team-A/online-boutique`)  
**Repositorio:** `https://github.com/Unal-SQ-Team-A/online-boutique.git`  
**Versión base probada:** Rama `main` (commit `c7cb6d5b`, Release `v0.10.7`)  
**Fecha de ejecución:** 2026-11-24 / 2026-11-26  

---

## 1. Ficha de Componente: `C-LOG-1` (`shippingservice`)

### A. Datos generales

| Campo | Valor |
| --- | --- |
| ID del componente | `C-LOG-1` |
| Responsable | Equipo A — Calidad de Software |
| Capa | Lógica (`LOG`) |
| Tipo | Servicio de dominio / cálculo de tarifa y generación de guía |
| Ubicación en el código | `src/shippingservice/main.go` (`GetQuote`, `ShipOrder`), `src/shippingservice/quote.go`, `src/shippingservice/tracker.go` |
| Qué hace (una frase) | Calcula la cotización de envío en USD a partir de la cantidad de ítems del carrito y genera un identificador de rastreo (`TrackingId`) para órdenes de envío. |
| Dependencias | `context.Context`, `pb` (`genproto`), `math/rand`, `sirupsen/logrus` (logger global) |
| Razón de selección por riesgo | **Criticidad financiera y operativa:** determina el costo de envío cobrado al cliente en el flujo de checkout y emite el identificador único de seguimiento de la orden. |

### B. Contrato

> Todo enunciado cuya fuente sea únicamente la inspección del código fuente se marca como **(SUPOSICIÓN)**.

| ID | Tipo | Enunciado | Fuente |
| --- | --- | --- | --- |
| `PRE-1` | Precondición | `in` (`*pb.GetQuoteRequest`) no es `nil`; `in.Items` contiene `0` o más ítems con `Quantity >= 0`. | Código fuente `main.go:119-138` **(SUPOSICIÓN)** |
| `PRE-2` | Precondición | En `ShipOrder`, `in` (`*pb.ShipOrderRequest`) e `in.Address` no son `nil`. | Código fuente `main.go:142-153` **(SUPOSICIÓN)** |
| `POST-1` | Postcondición | `GetQuote` retorna `*pb.GetQuoteResponse` con `CurrencyCode == "USD"`, `Units == 0` y `Nanos == 0` cuando la suma total de cantidades es `0`; o `Units == 8` y `Nanos == 990000000` (`$8.99`) cuando la suma es distinta de `0`. | Código fuente `quote.go:34-47`, `main.go:124-136` **(SUPOSICIÓN)** |
| `POST-2` | Postcondición | `ShipOrder` retorna un `TrackingId` con formato `^[A-Z]{2}-<len(salt)>\d{3}-<len(salt)/2>\d{7}$`, donde `salt = fmt.Sprintf("%s, %s, %s", StreetAddress, City, State)`. | Código fuente `main.go:146-152`, `tracker.go:23-32` **(SUPOSICIÓN)** |
| `INV-1` | Invariante | `GetQuote` es determinista e idempotente: para una misma entrada produce exactamente el mismo `CostUsd`, sin efectos secundarios ni `Units < 0` ni `Nanos` fuera de `[0, 999999999]`. | Código fuente `quote.go:42-47` **(SUPOSICIÓN)** |
| `EXC-1` | Excepción | Si `in.Items` está vacío o la suma de cantidades es `0`, no retorna error gRPC sino tarifa `$0.00`. Si `Quantity < 0` o `Address` es `nil`/vacío en `GetQuote`, la implementación actual no valida ni retorna `codes.InvalidArgument`. | Código fuente `main.go:124-136`, `quote.go:34-39` **(SUPOSICIÓN)** |

### C. Casos de prueba

| ID | Componente | Condición | Técnica | Entradas | Resultado esperado | Contrato |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-LOG-01` | `C-LOG-1` | Frontera mínima válida: 1 ítem con `Quantity=1` y dirección válida | `VL` | `Items=[{OLJCESPC7Z, 1}]`, dirección válida | `CostUsd = USD 8.990000000`, `err == nil` | `PRE-1, POST-1, INV-1` |
| `TC-LOG-02` | `C-LOG-1` | Múltiples ítems válidos (total 5 unidades) | `PE` | `Items=[{OLJCESPC7Z, 2}, {66VCHSJNUP, 3}]` | `CostUsd = USD 8.990000000`, `err == nil` | `PRE-1, POST-1` |
| `TC-LOG-03` | `C-LOG-1` | Gran volumen (1000 unidades) sin desbordamiento | `VL` | `Items=[{OLJCESPC7Z, 500}, {1YMWWN1N4O, 500}]` | `CostUsd = USD 8.990000000`, `Units >= 0`, `Nanos ∈ [0, 999999999]` | `PRE-1, POST-1, INV-1` |
| `TC-LOG-04` | `C-LOG-1` | Llamadas consecutivas idénticas (idempotencia) | `INV` | `Items=[{23, 1}, {46, 3}]` ejecutado 2 veces | `res1.CostUsd == res2.CostUsd` | `INV-1` |
| `TC-LOG-05` | `C-LOG-1` | Carrito vacío (`items=[]`) | `VL / EX` | `Items=[]` | `CostUsd = USD 0.000000000`, `err == nil` | `POST-1, EXC-1` |
| `TC-LOG-06` | `C-LOG-1` | Ítem con cantidad cero (`quantity=0`) | `VL / EX` | `Items=[{OLJCESPC7Z, 0}]` | `CostUsd = USD 0.000000000`, `err == nil` | `POST-1, EXC-1` |
| `TC-LOG-07` | `C-LOG-1` | Ítem con cantidad negativa (`quantity=-5`) | `VL / EX` | `Items=[{OLJCESPC7Z, -5}]` | Documenta comportamiento actual: no retorna error gRPC y cobra `$8.99` | `EXC-1` |
| `TC-LOG-08` | `C-LOG-1` | Dirección `nil` o con campos vacíos en `GetQuote` | `PE / EX` | `Address=nil` y `Address={}` con 1 ítem | Documenta comportamiento actual: ignora `Address` y retorna `$8.99` | `EXC-1` |
| `TC-LOG-09` | `C-LOG-1` | Formato exacto de `TrackingId` en `ShipOrder` e invariancia de prefijos | `PE / VL` | Dirección `"1600 Amphitheatre Parkway, Mountain View, CA"` (`len=44`) | `TrackingId` cumple `^[A-Z]{2}-44\d{3}-22\d{7}$` en llamadas consecutivas | `PRE-2, POST-2` |

*(Además se conservan las pruebas base del repositorio: `TestShipOrder`, `TestTrackingIdFormat`, `TestTrackingIdUniqueness`, `TestCreateQuoteFromFloat`, `TestCreateQuoteFromCount`, `TestGetRandomLetterCode`, `TestGetRandomNumber`, `TestQuoteString`).*

### D. Aislamiento

| Dependencia | Tipo de doble | Qué simula | Suposición sobre la dependencia real |
| --- | --- | --- | --- |
| Servidor gRPC / red | Llamada directa en memoria (`s := server{}`) | Invocación directa de métodos RPC sin abrir sockets | El transporte gRPC deserializa correctamente `GetQuoteRequest` y `ShipOrderRequest`. |
| `context.Context` | Dummy (`context.Background()`) | Contexto de ejecución sin cancelación ni deadlines | Los métodos `GetQuote` y `ShipOrder` no requieren metadatos ni cancelación activa en contexto. |
| `math/rand` | Generador estándar (`rand.Seed(42)` + validación invariante por regex) | Secuencia pseudoaleatoria para letras y dígitos del `TrackingId` | `rand.Intn` retorna enteros uniformes en `[0, n)`. |

Control de no determinismo:
- **Reloj:** No depende del reloj del sistema para la lógica de negocio (solo el logger imprime timestamp).
- **Valores aleatorios o generados:** `TestShipOrder_ExactTrackingID` valida mediante expresión regular estricta (`^[A-Z]{2}-44\d{3}-22\d{7}$`) los segmentos determinísticos (`len(salt)` y `len(salt)/2`) y la longitud exacta de los segmentos aleatorios.
- **Orden de ejecución:** Cada `t.Run` construye su propia instancia de `server{}` y sus propios structs de entrada en memoria; no hay estado compartido mutable.

### E. Implementación y ejecución

| Campo | Valor |
| --- | --- |
| Framework de pruebas | `testing` (Go estándar `go1.27.4`) |
| Archivo de tests | `src/shippingservice/shippingservice_test.go` |
| Comando para correr solo esta suite | `cd src/shippingservice && go test -v -coverprofile=coverage.out .` |
| Resultado | Todas las pruebas pasan (`PASS`, 0 fallos) — ejecutado 2026-11-26 |

### F. Adecuación

| Métrica | Resultado | Análisis |
| --- | --- | --- |
| Cobertura de sentencias/ramas (`go tool cover -func=coverage.out`) | **40.6%** total del paquete (`100.0%` en `GetQuote`, `ShipOrder`, `quote.go` y `tracker.go`) | Las funciones de lógica de negocio (`GetQuote`, `ShipOrder`, `CreateQuoteFromCount`, `CreateQuoteFromFloat`, `CreateTrackingId`, `getRandomLetterCode`, `getRandomNumber`, `Quote.String`) tienen **100% de cobertura**. Permanece sin cubrir (`0%`) únicamente el código de infraestructura de arranque/observabilidad (`main`, `Check`, `Watch`, `initStats`, `initTracing`, `initProfiling`). |
| Mutación (`gremlins unleash`) — Ejecución inicial | **Test efficacy: 85.71%** (6 Killed, 1 Lived, 1 Timed out, 189 Not covered) | Sobrevivió `ARITHMETIC_BASE` en `tracker.go:29:12` (`len(salt)/2` mutado a `len(salt)*2`), porque para el `salt` de `TestShipOrder` (`len=20`) tanto `20/2=10` como `20*2=40` tienen 2 dígitos y cumplían `len == 18`. El mutante `TIMED OUT` en `tracker.go:42:27` (`i++` a `i--`) genera un bucle infinito esperado. |
| Mutación (`gremlins unleash`) — Ejecución reforzada | **Test efficacy: 100.00%** (**7 Killed, 0 Lived**, 1 Timed out, 189 Not covered, Mutator coverage: 3.57%) | Los 189 `NOT COVERED` corresponden a código autogenerado en `genproto/` (178) e infraestructura de arranque en `main.go` (11). |
| Tests reforzados por la mutación | `TestShipOrder_ExactTrackingID` (`[TC-LOG-09]`) | Mata el mutante `ARITHMETIC_BASE` en `tracker.go:29:12` al exigir el valor exacto `22` (`len(salt)/2`) en la expresión regular `^[A-Z]{2}-44\d{3}-22\d{7}$`. |

### G. Hallazgos

| Tipo | Descripción | Esperado | Observado | Caso |
| --- | --- | --- | --- | --- |
| Defecto | `GetQuote` acepta cantidades negativas en `Items` | Retornar error gRPC `INVALID_ARGUMENT` ante `Quantity < 0` | No retorna error y cobra `$8.99` porque `CreateQuoteFromCount` solo evalúa `count == 0` | `TC-LOG-07` |
| Problema de especificación | `GetQuote` no valida `in.Address` | Validar campos obligatorios de dirección o documentar que no se usa | Acepta `Address == nil` o con campos vacíos y retorna `$8.99` | `TC-LOG-08` |
| Dificultad de prueba | `math/rand.Seed` es no-op en Go 1.20+ (`randautoseed=1`) | Poder fijar semilla global con `rand.Seed(42)` para reproducibilidad exacta | Dos llamadas consecutivas generan prefijos de letras/dígitos distintos; se mitigó validando por regex estricta los segmentos determinísticos | `TC-LOG-09` |

---

## 2. Ficha de Componente: `C-LOG-2` (`recommendationservice`)

### A. Datos generales

| Campo | Valor |
| --- | --- |
| ID del componente | `C-LOG-2` |
| Responsable | Equipo A — Calidad de Software |
| Capa | Lógica (`LOG`) |
| Tipo | Servicio de dominio (`RecommendationService.ListRecommendations`) |
| Ubicación en el código | `src/recommendationservice/recommendation_server.py:RecommendationService.ListRecommendations` |
| Qué hace (una frase) | Obtiene el catálogo de productos desde `ProductCatalogService`, excluye los productos ya presentes en el carrito del usuario y retorna hasta 5 recomendaciones aleatorias sin duplicados. |
| Dependencias | `product_catalog_stub` (gRPC hacia `ProductCatalogService`), `grpc.ServicerContext`, `random.sample`, `logger` (`getJSONLogger`) |
| Razón de selección por riesgo | **Complejidad lógica y dependencia externa:** filtra conjuntos dinámicos, muestrea aleatoriamente sin repetición bajo límite superior (`max_responses = 5`) y depende de una llamada gRPC síncrona a otro microservicio. |

### B. Contrato

> Todo enunciado cuya fuente sea únicamente la inspección del código fuente se marca como **(SUPOSICIÓN)**.

| ID | Tipo | Enunciado | Fuente |
| --- | --- | --- | --- |
| `PRE-1` | Precondición | `request` es un `demo_pb2.ListRecommendationsRequest` válido y `product_catalog_stub` está inicializado y responde a `ListProducts(Empty())`. | Código fuente `recommendation_server.py:70-74` **(SUPOSICIÓN)** |
| `POST-1` | Postcondición | Retorna `demo_pb2.ListRecommendationsResponse` cuyos `product_ids` pertenecen al catálogo menos `request.product_ids`, sin duplicados y con longitud `min(5, len(filtered_products))`. | Código fuente `recommendation_server.py:71-86` **(SUPOSICIÓN)** |
| `INV-1` | Invariante | Ningún ID presente en `request.product_ids` aparece en `response.product_ids`, y `len(response.product_ids) <= 5`. | Código fuente `recommendation_server.py:71,75,77` **(SUPOSICIÓN)** |
| `EXC-1` | Excepción | Si `product_catalog_stub.ListProducts` lanza `grpc.RpcError`, la excepción se propaga sin ser capturada ni ocultada. | Código fuente `recommendation_server.py:73` **(SUPOSICIÓN)** |

### C. Casos de prueba

| ID | Componente | Condición | Técnica | Entradas | Resultado esperado | Contrato |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-LOG-09` | `C-LOG-2` | Filtrado normal excluyendo producto en carrito | `PE` | Catálogo `["P1","P2","P3","P4"]`, carrito `["P1"]` | Retorna 3 IDs (`{"P2","P3","P4"}`), `"P1"` excluido, `ListProducts(Empty())` llamado 1 vez | `PRE-1, POST-1, INV-1` |
| `TC-LOG-10` | `C-LOG-2` | Carrito vacío | `VL` | Catálogo `["P1","P2"]`, carrito `[]` | Retorna `{"P1","P2"}` (longitud 2) | `POST-1` |
| `TC-LOG-11` | `C-LOG-2` | Catálogo coincide totalmente con carrito | `VL` | Catálogo `["P1","P2"]`, carrito `["P1","P2"]` | Retorna lista vacía `[]` | `POST-1, INV-1` |
| `TC-LOG-12` | `C-LOG-2` | Catálogo vacío | `VL / EX` | Catálogo `[]`, carrito `["P1"]` | Retorna lista vacía `[]` | `POST-1, INV-1` |
| `TC-LOG-13` | `C-LOG-2` | Falla de dependencia gRPC (`ProductCatalogService`) | `EX` | `ListProducts` lanza `DummyRpcError(grpc.RpcError)` | Se propaga `grpc.RpcError` sin ocultarse | `EXC-1` |
| `TC-LOG-14` | `C-LOG-2` | Límite superior de recomendaciones (`max_responses=5`) | `VL` | Catálogo `P1..P10`, carrito `[]` | Exactamente 5 recomendaciones únicas pertenecientes al catálogo | `POST-1, INV-1` |
| `TC-LOG-16` | `C-LOG-2` | Exactitud del tamaño de muestra con filtrado previo | `VL / PE` | Catálogo `P1..P8`, carrito `["P1","P2"]` | `len(res.product_ids) == 5`, únicos, sin `"P1"` ni `"P2"` | `POST-1, INV-1` |
| `TC-LOG-17` | `C-LOG-2` | Filtrado estricto (3 elegibles) y determinismo con semilla | `PE / INV` | Catálogo `P1..P5`, carrito `["P2","P4"]`, `random.seed(42)` | `len(res.product_ids) == 3`, `{"P1","P3","P5"}`, misma salida al repetir con semilla `42` | `POST-1, INV-1` |

### D. Aislamiento

| Dependencia | Tipo de doble | Qué simula | Suposición sobre la dependencia real |
| --- | --- | --- | --- |
| `product_catalog_stub` | Mock (`unittest.mock.MagicMock` inyectado con `patch.object(..., create=True)`) | Respuesta `ListProductsResponse` en memoria o excepción `DummyRpcError(grpc.RpcError)` | `ProductCatalogService.ListProducts` recibe `demo_pb2.Empty()` y retorna un objeto con atributo `.products` iterable de `.id`. |
| `grpc_context` | Mock (`MagicMock`) | Contexto de llamada gRPC del servidor | `ListRecommendations` no invoca métodos destructivos sobre `context` en flujo normal. |
| `random.sample` | Semilla controlada (`random.seed(42)` en fixture `autouse=True`) | Selección aleatoria determinista de índices | `random.sample` utiliza el generador global del módulo `random`. |

Control de no determinismo:
- **Reloj:** No utilizado por `ListRecommendations`.
- **Valores aleatorios o generados:** Fixture `deterministic_random` (`autouse=True`) fija `random.seed(42)` antes de cada test, y `TC-LOG-17` verifica repetibilidad explícita restableciendo `random.seed(42)`.
- **Orden de ejecución:** Cada prueba crea su propio `mock_stub` y parchea `recommendation_server.product_catalog_stub` dentro de un bloque `with patch.object(...)`.

### E. Implementación y ejecución

| Campo | Valor |
| --- | --- |
| Framework de pruebas | `pytest` (`9.2.0`) + `pytest-cov` (`7.1.0`) |
| Archivo de tests | `src/recommendationservice/tests/test_recommendation.py` |
| Comando para correr solo esta suite | `cd src/recommendationservice && pytest --cov=. --cov-report=term-missing -v` |
| Resultado | **8 passed** (0 failed) — ejecutado 2026-11-24 |

### F. Adecuación

| Métrica | Resultado | Análisis |
| --- | --- | --- |
| Cobertura (`pytest --cov=. --cov-report=term-missing`) | `recommendation_server.py`: **43%** (total del paquete: **48%**, `logger.py`: **95%**) | `ListRecommendations` queda cubierto al 100%; permanecen sin cubrir `initStackdriverProfiling` (líneas 44-67), `Check`/`Watch` (89, 93) y el bloque `if __name__ == "__main__":` (98-156) porque pertenecen al ciclo de vida del servidor y profiling. |
| Mutación (`mutmut run --paths-to-mutate=recommendation_server.py`) | **20.69%** (**12 Killed, 46 Survived**, 0 Timeout, 0 Suspicious, 58 Total) | Los 46 mutantes sobrevivientes (`1, 3-5, 16, 18-58`) corresponden al logger a nivel de módulo (`1, 3-5`), `logger.info` dentro de `ListRecommendations` (`16, 18`, mutantes equivalentes respecto a la respuesta gRPC) y a las funciones de infraestructura no cubiertas (`19-58`). |
| Tests reforzados por la mutación | `test_tc_log_16_exactitud_tamano_muestra`, `test_tc_log_17_filtrado_estricto_y_determinismo` | Refuerzan las aserciones estrictas sobre `len(res.product_ids) == 5` y `len(res.product_ids) == 3`, la exclusión de ítems del carrito y el determinismo bajo `random.seed(42)`. |

### G. Hallazgos

| Tipo | Descripción | Esperado | Observado | Caso |
| --- | --- | --- | --- | --- |
| Problema de especificación | Manejo de fallas de `ProductCatalogService` | Definir si `ListRecommendations` debe capturar `grpc.RpcError` o propagarlo | Propaga `grpc.RpcError` directamente al invocador sin manejo o fallback | `TC-LOG-13` |
| Dificultad de prueba | `product_catalog_stub` se crea en `__main__` como variable global del módulo | Inyección de dependencias en el constructor de `RecommendationService` | Al importar `recommendation_server`, `product_catalog_stub` no existe y requiere `patch.object(..., create=True)` | `TC-LOG-09..17` |

---

## 3. Ejecución unificada (CI / GitHub Actions)

Se implementó el workflow [`.github/workflows/component-verification.yaml`](file:///C:/Users/GAMEZONE/Documents/JRCR/Diplomado/Calidad%20Software/Proyecto%20Piloto/online-boutique/.github/workflows/component-verification.yaml) que ejecuta automáticamente las pruebas unitarias, reportes de cobertura y pruebas de mutación para ambos componentes (`shippingservice` y `recommendationservice`) y publica los reportes como artefactos descargables.
