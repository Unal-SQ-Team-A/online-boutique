"""Pruebas unitarias en estricto aislamiento para C-LOG-2 (recommendationservice:ListRecommendations)."""

import os
import random
import sys
from unittest.mock import MagicMock, patch

import grpc
import pytest

# Asegurar que el directorio padre (src/recommendationservice) esté en sys.path
SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

import demo_pb2  # noqa: E402
import recommendation_server  # noqa: E402
from recommendation_server import RecommendationService  # noqa: E402


class DummyRpcError(grpc.RpcError):
    """Excepción simulada de gRPC para pruebas en aislamiento."""


def _build_catalog_response(product_ids: list[str]) -> demo_pb2.ListProductsResponse:
    """Construye un ListProductsResponse en memoria a partir de una lista de IDs."""
    products = [demo_pb2.Product(id=pid) for pid in product_ids]
    return demo_pb2.ListProductsResponse(products=products)


@pytest.fixture(autouse=True)
def deterministic_random():
    """Fija la semilla de random antes de cada prueba para garantizar determinismo."""
    random.seed(42)


@pytest.fixture
def service() -> RecommendationService:
    """Instancia directa del servicer sin levantar servidor gRPC."""
    return RecommendationService()


@pytest.fixture
def grpc_context() -> MagicMock:
    """Contexto gRPC simulado en memoria."""
    return MagicMock()


def test_tc_log_09_filtrado_normal(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-09] Catálogo=[P1,P2,P3,P4], Carrito=[P1] -> subconjunto de [P2,P3,P4] sin P1."""
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(["P1", "P2", "P3", "P4"])

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=["P1"])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        response = service.ListRecommendations(request, grpc_context)

    returned = list(response.product_ids)
    assert "P1" not in returned
    assert len(returned) == 3
    assert set(returned) == {"P2", "P3", "P4"}
    mock_stub.ListProducts.assert_called_once_with(demo_pb2.Empty())


def test_tc_log_10_carrito_vacio(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-10] Catálogo=[P1,P2], Carrito=[] -> retorna [P1, P2]."""
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(["P1", "P2"])

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=[])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        response = service.ListRecommendations(request, grpc_context)

    returned = list(response.product_ids)
    assert len(returned) == 2
    assert set(returned) == {"P1", "P2"}


def test_tc_log_11_catalogo_coincide_totalmente_con_carrito(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-11] Catálogo=[P1,P2], Carrito=[P1,P2] -> retorna lista vacía []."""
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(["P1", "P2"])

    request = demo_pb2.ListRecommendationsRequest(
        user_id="user-1", product_ids=["P1", "P2"]
    )

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        response = service.ListRecommendations(request, grpc_context)

    assert list(response.product_ids) == []


def test_tc_log_12_catalogo_vacio(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-12] Catálogo=[], Carrito=[P1] -> retorna lista vacía []."""
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response([])

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=["P1"])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        response = service.ListRecommendations(request, grpc_context)

    assert list(response.product_ids) == []


def test_tc_log_13_falla_dependencia_grpc(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-13] ProductCatalogService lanza grpc.RpcError -> se propaga sin ocultarse."""
    mock_stub = MagicMock()
    mock_stub.ListProducts.side_effect = DummyRpcError("ProductCatalogService unavailable")

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=["P1"])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        with pytest.raises(grpc.RpcError):
            service.ListRecommendations(request, grpc_context)


def test_tc_log_14_limite_superior_recomendaciones(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-14] Catálogo con 10 ítems y Carrito=[] -> máximo 5 recomendaciones únicas."""
    catalog_ids = [f"P{i}" for i in range(1, 11)]
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(catalog_ids)

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=[])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        response = service.ListRecommendations(request, grpc_context)

    returned = list(response.product_ids)
    assert len(returned) <= 5
    assert len(returned) == 5
    assert len(set(returned)) == len(returned)
    assert set(returned).issubset(set(catalog_ids))


def test_tc_log_16_exactitud_tamano_muestra(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-16] Catálogo con 8 ítems y Carrito=[P1,P2] -> exactamente 5 recomendaciones únicas."""
    catalog_ids = [f"P{i}" for i in range(1, 9)]
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(catalog_ids)

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=["P1", "P2"])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        res = service.ListRecommendations(request, grpc_context)

    assert len(res.product_ids) == 5
    assert len(set(res.product_ids)) == 5
    assert "P1" not in res.product_ids
    assert "P2" not in res.product_ids
    assert set(res.product_ids).issubset(set(catalog_ids) - {"P1", "P2"})


def test_tc_log_17_filtrado_estricto_y_determinismo(
    service: RecommendationService, grpc_context: MagicMock
) -> None:
    """[TC-LOG-17] Filtrado estricto (3 ítems elegibles) y determinismo con semilla fija."""
    catalog_ids = ["P1", "P2", "P3", "P4", "P5"]
    mock_stub = MagicMock()
    mock_stub.ListProducts.return_value = _build_catalog_response(catalog_ids)

    request = demo_pb2.ListRecommendationsRequest(user_id="user-1", product_ids=["P2", "P4"])

    with patch.object(recommendation_server, "product_catalog_stub", mock_stub, create=True):
        random.seed(42)
        res = service.ListRecommendations(request, grpc_context)
        random.seed(42)
        res_repeat = service.ListRecommendations(request, grpc_context)

    assert len(res.product_ids) == 3
    assert "P2" not in res.product_ids
    assert "P4" not in res.product_ids
    assert set(res.product_ids) == {"P1", "P3", "P5"}
    assert list(res.product_ids) == list(res_repeat.product_ids)
