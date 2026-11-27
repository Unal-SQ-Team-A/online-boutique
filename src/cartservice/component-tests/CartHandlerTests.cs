using System.Threading.Tasks;
using cartservice.cartstore;
using Grpc.Core;
using Hipstershop;
using NSubstitute;
using Xunit;
using CartHandler = cartservice.services.CartService;

namespace cartservice.componenttests
{
    /// <summary>
    /// C-DAT-2 gRPC handler (cartservice.services.CartService).
    /// Dependency ICartStore replaced by an NSubstitute double: a stub for the results it returns,
    /// a mock where the behavior of interest is the interaction ("the store was called once with ...").
    /// The ServerCallContext is never used by the handler, so null is passed.
    /// </summary>
    public class CartHandlerTests
    {
        private static readonly RpcException StoreFailure =
            new RpcException(new Status(StatusCode.FailedPrecondition, "store down"));

        [Fact, Trait("TC", "TC-DAT-22")]
        public async Task TC_DAT_22_AddItem_DelegatesToStoreWithRequestData()
        {
            var store = Substitute.For<ICartStore>();
            var handler = new CartHandler(store);
            var request = new AddItemRequest { UserId = "u1", Item = new CartItem { ProductId = "p1", Quantity = 3 } };

            var reply = await handler.AddItem(request, null);

            Assert.NotNull(reply);
            await store.Received(1).AddItemAsync("u1", "p1", 3);
        }

        [Fact, Trait("TC", "TC-DAT-23")]
        public async Task TC_DAT_23_GetCart_ReturnsTheCartOfTheStore()
        {
            var store = Substitute.For<ICartStore>();
            var expected = new Cart { UserId = "u1" };
            expected.Items.Add(new CartItem { ProductId = "p1", Quantity = 2 });
            store.GetCartAsync("u1").Returns(Task.FromResult(expected));
            var handler = new CartHandler(store);

            var cart = await handler.GetCart(new GetCartRequest { UserId = "u1" }, null);

            Assert.Same(expected, cart);
            await store.Received(1).GetCartAsync("u1");
        }

        [Fact, Trait("TC", "TC-DAT-24")]
        public async Task TC_DAT_24_EmptyCart_DelegatesToStore()
        {
            var store = Substitute.For<ICartStore>();
            var handler = new CartHandler(store);

            var reply = await handler.EmptyCart(new EmptyCartRequest { UserId = "u1" }, null);

            Assert.NotNull(reply);
            await store.Received(1).EmptyCartAsync("u1");
        }

        [Fact, Trait("TC", "TC-DAT-25")]
        public async Task TC_DAT_25_AddItem_StoreFails_ExceptionPropagatesUnchanged()
        {
            var store = Substitute.For<ICartStore>();
            store.AddItemAsync(Arg.Any<string>(), Arg.Any<string>(), Arg.Any<int>())
                 .Returns(Task.FromException(StoreFailure));
            var handler = new CartHandler(store);
            var request = new AddItemRequest { UserId = "u1", Item = new CartItem { ProductId = "p1", Quantity = 1 } };

            var ex = await Assert.ThrowsAsync<RpcException>(() => handler.AddItem(request, null));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-26")]
        public async Task TC_DAT_26_GetCart_StoreFails_ExceptionPropagatesUnchanged()
        {
            var store = Substitute.For<ICartStore>();
            store.GetCartAsync(Arg.Any<string>()).Returns(Task.FromException<Cart>(StoreFailure));
            var handler = new CartHandler(store);

            var ex = await Assert.ThrowsAsync<RpcException>(
                () => handler.GetCart(new GetCartRequest { UserId = "u1" }, null));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-27")]
        public async Task TC_DAT_27_EmptyCart_StoreFails_ExceptionPropagatesUnchanged()
        {
            var store = Substitute.For<ICartStore>();
            store.EmptyCartAsync(Arg.Any<string>()).Returns(Task.FromException(StoreFailure));
            var handler = new CartHandler(store);

            var ex = await Assert.ThrowsAsync<RpcException>(
                () => handler.EmptyCart(new EmptyCartRequest { UserId = "u1" }, null));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
        }
    }
}
