// Copyright 2018 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"math/rand"
	"regexp"
	"testing"

	"golang.org/x/net/context"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/shippingservice/genproto"
)

// TestGetQuote ejecuta la matriz formal de pruebas unitarias en aislamiento
// sobre el método GetQuote de shippingservice sin levantar sockets de red.
func TestGetQuote(t *testing.T) {
	// Semilla fija para garantizar determinismo en cualquier uso de math/rand.
	//nolint:staticcheck
	rand.Seed(42)

	s := server{}
	ctx := context.Background()

	validAddress := &pb.Address{
		StreetAddress: "1600 Amphitheatre Parkway",
		City:          "Mountain View",
		State:         "CA",
		Country:       "United States",
		ZipCode:       94043,
	}

	t.Run("[TC-LOG-01] Frontera minima valida (BVA): 1 item quantity=1 y direccion valida", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "OLJCESPC7Z", Quantity: 1},
			},
		}

		res, err := s.GetQuote(ctx, req)
		if err != nil {
			t.Fatalf("error inesperado en GetQuote: %v", err)
		}
		if res == nil || res.CostUsd == nil {
			t.Fatalf("respuesta o CostUsd nil")
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		if res.CostUsd.GetUnits() < 0 {
			t.Errorf("units = %d, esperado >= 0", res.CostUsd.GetUnits())
		}
		if res.CostUsd.GetNanos() < 0 || res.CostUsd.GetNanos() >= 1_000_000_000 {
			t.Errorf("nanos = %d, fuera de rango [0, 999999999]", res.CostUsd.GetNanos())
		}
		if res.CostUsd.GetUnits() != 8 || res.CostUsd.GetNanos() != 990000000 {
			t.Errorf("cotizacion = %d.%09d, esperado 8.990000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
	})

	t.Run("[TC-LOG-02] Multiples items (PE Valida): 2 items total 5 unidades", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "OLJCESPC7Z", Quantity: 2},
				{ProductId: "66VCHSJNUP", Quantity: 3},
			},
		}

		res, err := s.GetQuote(ctx, req)
		if err != nil {
			t.Fatalf("error inesperado en GetQuote: %v", err)
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		// La implementacion actual (CreateQuoteFromCount) aplica tarifa plana de $8.99 para todo count != 0.
		if res.CostUsd.GetUnits() != 8 || res.CostUsd.GetNanos() != 990000000 {
			t.Errorf("cotizacion = %d.%09d, esperado tarifa plana consistente 8.990000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
	})

	t.Run("[TC-LOG-03] Gran volumen (BVA Limite superior): 1000 items sin desbordamiento", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "OLJCESPC7Z", Quantity: 500},
				{ProductId: "1YMWWN1N4O", Quantity: 500},
			},
		}

		res, err := s.GetQuote(ctx, req)
		if err != nil {
			t.Fatalf("error inesperado en GetQuote con gran volumen: %v", err)
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		if res.CostUsd.GetUnits() < 0 || res.CostUsd.GetNanos() < 0 || res.CostUsd.GetNanos() >= 1_000_000_000 {
			t.Errorf("posible desbordamiento en Money: units=%d, nanos=%d", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
		if res.CostUsd.GetUnits() != 8 || res.CostUsd.GetNanos() != 990000000 {
			t.Errorf("cotizacion = %d.%09d, esperado 8.990000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
	})

	t.Run("[TC-LOG-04] Invariante de determinismo e idempotencia (INV-1)", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "23", Quantity: 1},
				{ProductId: "46", Quantity: 3},
			},
		}

		res1, err1 := s.GetQuote(ctx, req)
		res2, err2 := s.GetQuote(ctx, req)
		if err1 != nil || err2 != nil {
			t.Fatalf("errores inesperados en llamadas consecutivas: err1=%v, err2=%v", err1, err2)
		}
		if res1.CostUsd.GetUnits() != res2.CostUsd.GetUnits() ||
			res1.CostUsd.GetNanos() != res2.CostUsd.GetNanos() ||
			res1.CostUsd.GetCurrencyCode() != res2.CostUsd.GetCurrencyCode() {
			t.Errorf("violacion de idempotencia: res1=%v vs res2=%v", res1.CostUsd, res2.CostUsd)
		}
	})

	t.Run("[TC-LOG-05] Carrito vacio (BVA / Excepcional): items=[]", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items:   []*pb.CartItem{},
		}

		res, err := s.GetQuote(ctx, req)
		if err != nil {
			t.Fatalf("error inesperado para carrito vacio: %v", err)
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		// CreateQuoteFromCount(0) retorna costo base $0.00 sin error gRPC.
		if res.CostUsd.GetUnits() != 0 || res.CostUsd.GetNanos() != 0 {
			t.Errorf("carrito vacio retorno %d.%09d, esperado 0.000000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
	})

	t.Run("[TC-LOG-06] Item con cantidad cero (BVA / Excepcional): quantity=0", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "OLJCESPC7Z", Quantity: 0},
			},
		}

		res, err := s.GetQuote(ctx, req)
		if err != nil {
			t.Fatalf("error inesperado para quantity=0: %v", err)
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		// La suma de cantidades es 0, por lo que CreateQuoteFromCount(0) retorna $0.00.
		if res.CostUsd.GetUnits() != 0 || res.CostUsd.GetNanos() != 0 {
			t.Errorf("quantity=0 retorno %d.%09d, esperado 0.000000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
	})

	t.Run("[TC-LOG-07] Item con cantidad negativa (BVA / Excepcional): quantity=-5", func(t *testing.T) {
		req := &pb.GetQuoteRequest{
			Address: validAddress,
			Items: []*pb.CartItem{
				{ProductId: "OLJCESPC7Z", Quantity: -5},
			},
		}

		res, err := s.GetQuote(ctx, req)
		// Comportamiento actual observado: GetQuote no valida cantidades negativas y
		// CreateQuoteFromCount(-5) evalua count != 0 retornando $8.99 sin error gRPC.
		if err != nil {
			t.Fatalf("error inesperado en implementacion actual para quantity=-5: %v", err)
		}
		if res.CostUsd.GetCurrencyCode() != "USD" {
			t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
		}
		if res.CostUsd.GetUnits() != 8 || res.CostUsd.GetNanos() != 990000000 {
			t.Errorf("quantity=-5 retorno %d.%09d, esperado 8.990000000 segun logica actual", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
		}
		t.Log("HALLAZGO QA: GetQuote acepta quantity=-5 sin error INVALID_ARGUMENT y cobra $8.99 porque CreateQuoteFromCount solo verifica count == 0.")
	})

	t.Run("[TC-LOG-08] Direccion incompleta o nula (PE Invalida)", func(t *testing.T) {
		testCases := []struct {
			name    string
			address *pb.Address
		}{
			{
				name:    "Direccion nula (nil)",
				address: nil,
			},
			{
				name: "Direccion incompleta (campos vacios)",
				address: &pb.Address{
					StreetAddress: "",
					City:          "",
					State:         "",
					Country:       "",
					ZipCode:       0,
				},
			},
		}

		for _, tc := range testCases {
			t.Run(tc.name, func(t *testing.T) {
				req := &pb.GetQuoteRequest{
					Address: tc.address,
					Items: []*pb.CartItem{
						{ProductId: "OLJCESPC7Z", Quantity: 1},
					},
				}

				res, err := s.GetQuote(ctx, req)
				// GetQuote no inspecciona in.Address; calcula unicamente sobre Items.
				if err != nil {
					t.Fatalf("error inesperado para %s: %v", tc.name, err)
				}
				if res.CostUsd.GetCurrencyCode() != "USD" {
					t.Errorf("currency_code = %q, esperado %q", res.CostUsd.GetCurrencyCode(), "USD")
				}
				if res.CostUsd.GetUnits() != 8 || res.CostUsd.GetNanos() != 990000000 {
					t.Errorf("cotizacion = %d.%09d, esperado 8.990000000", res.CostUsd.GetUnits(), res.CostUsd.GetNanos())
				}
			})
		}
		t.Log("HALLAZGO QA: GetQuote ignora in.Address (incluso nil o vacia) sin retornar INVALID_ARGUMENT.")
	})
}

// TestShipOrder is a basic check on the ShipOrder RPC service.
func TestShipOrder(t *testing.T) {
	//nolint:staticcheck
	rand.Seed(42)
	s := server{}

	req := &pb.ShipOrderRequest{
		Address: &pb.Address{
			StreetAddress: "Muffin Man",
			City:          "London",
			State:         "",
			Country:       "England",
		},
		Items: []*pb.CartItem{
			{ProductId: "23", Quantity: 1},
			{ProductId: "46", Quantity: 3},
		},
	}

	res, err := s.ShipOrder(context.Background(), req)
	if err != nil {
		t.Errorf("TestShipOrder (%v) failed", err)
	}
	if len(res.TrackingId) != 18 {
		t.Errorf("TestShipOrder: Tracking ID is malformed - has %d characters, %d expected", len(res.TrackingId), 18)
	}
}

// TestTrackingIdFormat verifies the tracking ID matches the expected pattern.
func TestTrackingIdFormat(t *testing.T) {
	//nolint:staticcheck
	rand.Seed(42)
	pattern := regexp.MustCompile(`^[A-Z]{2}-\d+-\d+$`)

	for i := 0; i < 20; i++ {
		id := CreateTrackingId("test-salt-value")
		if !pattern.MatchString(id) {
			t.Errorf("CreateTrackingId: '%s' does not match expected pattern '[A-Z]{2}-\\d+-\\d+'", id)
		}
	}
}

// TestTrackingIdUniqueness checks that generated IDs are not all identical.
func TestTrackingIdUniqueness(t *testing.T) {
	//nolint:staticcheck
	rand.Seed(42)
	seen := make(map[string]bool)
	for i := 0; i < 50; i++ {
		id := CreateTrackingId("same-salt")
		seen[id] = true
	}
	if len(seen) < 2 {
		t.Errorf("CreateTrackingId: expected unique IDs but got %d distinct values out of 50", len(seen))
	}
}

// TestCreateQuoteFromFloat verifies quote creation from float values.
func TestCreateQuoteFromFloat(t *testing.T) {
	tests := []struct {
		name    string
		value   float64
		dollars uint32
		cents   uint32
	}{
		{"zero", 0.0, 0, 0},
		{"whole dollars", 10.0, 10, 0},
		{"with cents", 8.99, 8, 99},
		{"small value", 0.50, 0, 50},
		{"large value", 100.01, 100, 1},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			q := CreateQuoteFromFloat(tc.value)
			if q.Dollars != tc.dollars || q.Cents != tc.cents {
				t.Errorf("CreateQuoteFromFloat(%v) = $%d.%d, want $%d.%d",
					tc.value, q.Dollars, q.Cents, tc.dollars, tc.cents)
			}
		})
	}
}

// TestCreateQuoteFromCount verifies count-based quote generation.
func TestCreateQuoteFromCount(t *testing.T) {
	zeroQuote := CreateQuoteFromCount(0)
	if zeroQuote.Dollars != 0 || zeroQuote.Cents != 0 {
		t.Errorf("CreateQuoteFromCount(0) = %s, want $0.0", zeroQuote)
	}

	nonZeroQuote := CreateQuoteFromCount(5)
	if nonZeroQuote.Dollars == 0 && nonZeroQuote.Cents == 0 {
		t.Error("CreateQuoteFromCount(5) returned zero, expected a non-zero quote")
	}
}

// TestGetRandomLetterCode verifies the output is a valid uppercase letter.
func TestGetRandomLetterCode(t *testing.T) {
	//nolint:staticcheck
	rand.Seed(42)
	for i := 0; i < 100; i++ {
		code := getRandomLetterCode()
		if code < 65 || code > 90 {
			t.Errorf("getRandomLetterCode: got %d (%c), expected range 65-90 (A-Z)", code, code)
		}
	}
}

// TestGetRandomNumber verifies the output has the correct number of digits.
func TestGetRandomNumber(t *testing.T) {
	//nolint:staticcheck
	rand.Seed(42)
	for _, digits := range []int{1, 3, 5, 7, 10} {
		result := getRandomNumber(digits)
		if len(result) != digits {
			t.Errorf("getRandomNumber(%d) = '%s' (len %d), expected length %d",
				digits, result, len(result), digits)
		}
	}
}

// TestQuoteString verifies the string representation of a Quote.
func TestQuoteString(t *testing.T) {
	q := Quote{Dollars: 8, Cents: 99}
	expected := "$8.99"
	if q.String() != expected {
		t.Errorf("Quote.String() = '%s', want '%s'", q.String(), expected)
	}
}

// TestShipOrder_ExactTrackingID verifies [TC-LOG-09] strict tracking ID format and determinism.
func TestShipOrder_ExactTrackingID(t *testing.T) {
	s := server{}
	ctx := context.Background()
	req := &pb.ShipOrderRequest{
		Address: &pb.Address{
			StreetAddress: "1600 Amphitheatre Parkway",
			City:          "Mountain View",
			State:         "CA",
			Country:       "United States",
			ZipCode:       94043,
		},
		Items: []*pb.CartItem{
			{ProductId: "OLJCESPC7Z", Quantity: 1},
		},
	}

	// baseAddress = "1600 Amphitheatre Parkway, Mountain View, CA" -> len = 44, len/2 = 22.
	exactPattern := regexp.MustCompile(`^[A-Z]{2}-44\d{3}-22\d{7}$`)

	res1, err := s.ShipOrder(ctx, req)
	if err != nil {
		t.Fatalf("error inesperado en ShipOrder: %v", err)
	}
	if !exactPattern.MatchString(res1.TrackingId) {
		t.Errorf("TrackingId %q no cumple el formato estricto ^[A-Z]{2}-44\\d{3}-22\\d{7}$", res1.TrackingId)
	}

	// Verificar que los segmentos deterministicos (len=44, len/2=22) se mantienen en llamadas consecutivas.
	res2, err := s.ShipOrder(ctx, req)
	if err != nil {
		t.Fatalf("error inesperado en segunda llamada a ShipOrder: %v", err)
	}
	if !exactPattern.MatchString(res2.TrackingId) {
		t.Errorf("TrackingId %q no cumple el formato estricto ^[A-Z]{2}-44\\d{3}-22\\d{7}$ en segunda llamada", res2.TrackingId)
	}
}
