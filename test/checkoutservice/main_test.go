package main

import (
	"context"
	"errors"
	"net"
	"testing"

	"github.com/google/uuid"
	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

func TestPlaceOrder(t *testing.T) {
	t.Run("CHECKOUT-001 successful order", func(t *testing.T) {
		service, doubles := newCheckoutTestService(t)
		request := checkoutRequest()

		response, err := service.PlaceOrder(context.Background(), request)
		if err != nil {
			t.Fatalf("PlaceOrder() returned an error: %v", err)
		}

		order := response.GetOrder()
		if _, err := uuid.Parse(order.GetOrderId()); err != nil {
			t.Fatalf("order ID %q is not a UUID: %v", order.GetOrderId(), err)
		}
		if order.GetShippingTrackingId() != "tracking-123" {
			t.Errorf("tracking ID = %q, want %q", order.GetShippingTrackingId(), "tracking-123")
		}
		if order.GetShippingCost().GetUnits() != 2 || order.GetShippingCost().GetCurrencyCode() != "USD" {
			t.Errorf("shipping cost = %v, want 2 USD", order.GetShippingCost())
		}
		if len(order.GetItems()) != 1 || order.GetItems()[0].GetCost().GetUnits() != 3 {
			t.Fatalf("order items = %v, want one item costing 3 USD", order.GetItems())
		}
		if order.GetItems()[0].GetItem().GetQuantity() != 2 {
			t.Errorf("ordered quantity = %d, want 2", order.GetItems()[0].GetItem().GetQuantity())
		}
		if doubles.payment.request.GetAmount().GetUnits() != 8 {
			t.Errorf("charged amount = %v, want 8 USD", doubles.payment.request.GetAmount())
		}
		if doubles.cart.emptyUserID != request.GetUserId() {
			t.Errorf("emptied cart for user %q, want %q", doubles.cart.emptyUserID, request.GetUserId())
		}
		if doubles.email.request.GetEmail() != request.GetEmail() {
			t.Errorf("confirmation email = %q, want %q", doubles.email.request.GetEmail(), request.GetEmail())
		}
		if doubles.shipping.shipRequest.GetAddress().GetCity() != request.GetAddress().GetCity() {
			t.Errorf("shipment city = %q, want %q",
				doubles.shipping.shipRequest.GetAddress().GetCity(), request.GetAddress().GetCity())
		}
	})

	t.Run("CHECKOUT-009 cart cleanup and email failures are non-fatal", func(t *testing.T) {
		service, doubles := newCheckoutTestService(t)
		doubles.cart.emptyErr = errors.New("cart storage unavailable")
		doubles.email.sendErr = errors.New("email service unavailable")

		response, err := service.PlaceOrder(context.Background(), checkoutRequest())
		if err != nil {
			t.Fatalf("PlaceOrder() returned an error for non-fatal failures: %v", err)
		}
		if response.GetOrder() == nil {
			t.Fatal("PlaceOrder() returned no order")
		}
		if doubles.email.request == nil {
			t.Fatal("order confirmation was not attempted")
		}
	})
}

func TestPlaceOrderDependencyFailures(t *testing.T) {
	tests := []struct {
		name       string
		configure  func(*checkoutTestDoubles)
		wantStatus codes.Code
	}{
		{
			name: "CHECKOUT-002 cart retrieval failure",
			configure: func(d *checkoutTestDoubles) {
				d.cart.getErr = errors.New("cart unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-003 product lookup failure",
			configure: func(d *checkoutTestDoubles) {
				d.products.getErr = errors.New("catalog unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-004 shipping quote failure",
			configure: func(d *checkoutTestDoubles) {
				d.shipping.quoteErr = errors.New("quote unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-005 item currency conversion failure",
			configure: func(d *checkoutTestDoubles) {
				d.currency.failOnCall = 1
				d.currency.convertErr = errors.New("conversion unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-006 shipping currency conversion failure",
			configure: func(d *checkoutTestDoubles) {
				d.currency.failOnCall = 2
				d.currency.convertErr = errors.New("conversion unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-007 payment failure",
			configure: func(d *checkoutTestDoubles) {
				d.payment.chargeErr = errors.New("payment unavailable")
			},
			wantStatus: codes.Internal,
		},
		{
			name: "CHECKOUT-008 shipment failure",
			configure: func(d *checkoutTestDoubles) {
				d.shipping.shipErr = errors.New("shipping unavailable")
			},
			wantStatus: codes.Unavailable,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			service, doubles := newCheckoutTestService(t)
			tt.configure(doubles)

			response, err := service.PlaceOrder(context.Background(), checkoutRequest())
			if err == nil {
				t.Fatal("PlaceOrder() returned no error")
			}
			if got := status.Code(err); got != tt.wantStatus {
				t.Errorf("PlaceOrder() status = %s, want %s", got, tt.wantStatus)
			}
			if response != nil {
				t.Errorf("PlaceOrder() response = %v, want nil", response)
			}
		})
	}
}

type checkoutTestDoubles struct {
	cart     *checkoutCartDouble
	products *checkoutProductDouble
	currency *checkoutCurrencyDouble
	shipping *checkoutShippingDouble
	payment  *checkoutPaymentDouble
	email    *checkoutEmailDouble
}

func newCheckoutTestService(t *testing.T) (*checkoutService, *checkoutTestDoubles) {
	t.Helper()

	doubles := &checkoutTestDoubles{
		cart: &checkoutCartDouble{
			cart: &pb.Cart{
				Items: []*pb.CartItem{{ProductId: "product-1", Quantity: 2}},
			},
		},
		products: &checkoutProductDouble{
			products: map[string]*pb.Product{
				"product-1": {
					Id:       "product-1",
					PriceUsd: &pb.Money{CurrencyCode: usdCurrency, Units: 3},
				},
			},
		},
		currency: &checkoutCurrencyDouble{},
		shipping: &checkoutShippingDouble{
			quote:      &pb.Money{CurrencyCode: usdCurrency, Units: 2},
			trackingID: "tracking-123",
		},
		payment: &checkoutPaymentDouble{transactionID: "transaction-123"},
		email:   &checkoutEmailDouble{},
	}

	listener := bufconn.Listen(1 << 20)
	server := grpc.NewServer()
	pb.RegisterCartServiceServer(server, doubles.cart)
	pb.RegisterProductCatalogServiceServer(server, doubles.products)
	pb.RegisterCurrencyServiceServer(server, doubles.currency)
	pb.RegisterShippingServiceServer(server, doubles.shipping)
	pb.RegisterPaymentServiceServer(server, doubles.payment)
	pb.RegisterEmailServiceServer(server, doubles.email)
	go func() {
		_ = server.Serve(listener)
	}()

	connection, err := grpc.NewClient(
		"passthrough:///checkout-test",
		grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
			return listener.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		server.Stop()
		_ = listener.Close()
		t.Fatalf("create gRPC test client: %v", err)
	}
	t.Cleanup(func() {
		_ = connection.Close()
		server.Stop()
		_ = listener.Close()
	})

	return &checkoutService{
		cartSvcConn:            connection,
		productCatalogSvcConn: connection,
		currencySvcConn:       connection,
		shippingSvcConn:       connection,
		paymentSvcConn:        connection,
		emailSvcConn:          connection,
	}, doubles
}

func checkoutRequest() *pb.PlaceOrderRequest {
	return &pb.PlaceOrderRequest{
		UserId:       "user-1",
		UserCurrency: usdCurrency,
		Address:      &pb.Address{StreetAddress: "1 Test St", City: "Test City", Country: "US", ZipCode: 12345},
		Email:        "user@example.test",
		CreditCard:   &pb.CreditCardInfo{CreditCardNumber: "test-card"},
	}
}

type checkoutCartDouble struct {
	pb.UnimplementedCartServiceServer
	cart        *pb.Cart
	getErr      error
	emptyErr    error
	emptyUserID string
}

func (d *checkoutCartDouble) GetCart(_ context.Context, _ *pb.GetCartRequest) (*pb.Cart, error) {
	return d.cart, d.getErr
}

func (d *checkoutCartDouble) EmptyCart(_ context.Context, request *pb.EmptyCartRequest) (*pb.Empty, error) {
	d.emptyUserID = request.GetUserId()
	return &pb.Empty{}, d.emptyErr
}

type checkoutProductDouble struct {
	pb.UnimplementedProductCatalogServiceServer
	products map[string]*pb.Product
	getErr   error
}

func (d *checkoutProductDouble) GetProduct(_ context.Context, request *pb.GetProductRequest) (*pb.Product, error) {
	if d.getErr != nil {
		return nil, d.getErr
	}
	product, ok := d.products[request.GetId()]
	if !ok {
		return nil, status.Error(codes.NotFound, "product not found")
	}
	return product, nil
}

type checkoutCurrencyDouble struct {
	pb.UnimplementedCurrencyServiceServer
	convertErr  error
	failOnCall  int
	convertCall int
}

func (d *checkoutCurrencyDouble) Convert(_ context.Context, request *pb.CurrencyConversionRequest) (*pb.Money, error) {
	d.convertCall++
	if d.convertErr != nil && (d.failOnCall == 0 || d.failOnCall == d.convertCall) {
		return nil, d.convertErr
	}
	return &pb.Money{
		CurrencyCode: request.GetToCode(),
		Units:        request.GetFrom().GetUnits(),
		Nanos:        request.GetFrom().GetNanos(),
	}, nil
}

type checkoutShippingDouble struct {
	pb.UnimplementedShippingServiceServer
	quote        *pb.Money
	trackingID   string
	quoteErr     error
	shipErr      error
	shipRequest  *pb.ShipOrderRequest
}

func (d *checkoutShippingDouble) GetQuote(_ context.Context, _ *pb.GetQuoteRequest) (*pb.GetQuoteResponse, error) {
	if d.quoteErr != nil {
		return nil, d.quoteErr
	}
	return &pb.GetQuoteResponse{CostUsd: d.quote}, nil
}

func (d *checkoutShippingDouble) ShipOrder(_ context.Context, request *pb.ShipOrderRequest) (*pb.ShipOrderResponse, error) {
	d.shipRequest = request
	if d.shipErr != nil {
		return nil, d.shipErr
	}
	return &pb.ShipOrderResponse{TrackingId: d.trackingID}, nil
}

type checkoutPaymentDouble struct {
	pb.UnimplementedPaymentServiceServer
	transactionID string
	chargeErr     error
	request       *pb.ChargeRequest
}

func (d *checkoutPaymentDouble) Charge(_ context.Context, request *pb.ChargeRequest) (*pb.ChargeResponse, error) {
	d.request = request
	if d.chargeErr != nil {
		return nil, d.chargeErr
	}
	return &pb.ChargeResponse{TransactionId: d.transactionID}, nil
}

type checkoutEmailDouble struct {
	pb.UnimplementedEmailServiceServer
	sendErr error
	request *pb.SendOrderConfirmationRequest
}

func (d *checkoutEmailDouble) SendOrderConfirmation(_ context.Context, request *pb.SendOrderConfirmationRequest) (*pb.Empty, error) {
	d.request = request
	return &pb.Empty{}, d.sendErr
}
