using System.Threading.Tasks;
using cartservice.cartstore;
using Grpc.Core;
using Hipstershop;
using NSubstitute;
using Xunit;
using static cartservice.componenttests.TestSupport;
using CartHandler = cartservice.services.CartService;

namespace cartservice.componenttests
{
    /// <summary>
    /// Cases whose expected result is an ASSUMED contract (the proto and the code say nothing, see the
    /// "ASSUMPTION" rows of the component sheet). They are expected to FAIL against the current code:
    /// each failure is a finding (expected vs observed) for section 9 of the report.
    /// Category "Defect" keeps them out of the green baseline (dotnet test --filter "Category!=Defect").
    /// </summary>
    [Trait("Category", "Defect")]
    public class SuspectedDefectTests
    {
        private const string User = "user-1";

        private static RedisCartStore NewStore() => new RedisCartStore(NewFakeCache());

        [Fact, Trait("TC", "TC-DAT-09")]
        public async Task TC_DAT_09_AddItem_QuantityZero_ShouldBeRejectedAsInvalidArgument()
        {
            var ex = await Assert.ThrowsAsync<RpcException>(() => NewStore().AddItemAsync(User, "p1", 0));
            Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-10")]
        public async Task TC_DAT_10_AddItem_NegativeQuantity_ShouldBeRejectedAsInvalidArgument()
        {
            var ex = await Assert.ThrowsAsync<RpcException>(() => NewStore().AddItemAsync(User, "p1", -1));
            Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-11")]
        public async Task TC_DAT_11_AddItem_QuantityOverflow_ShouldNeverLeaveANonPositiveQuantity()
        {
            var store = NewStore();
            await store.AddItemAsync(User, "p1", int.MaxValue);
            try { await store.AddItemAsync(User, "p1", 1); } catch (RpcException) { /* rejecting is acceptable */ }

            var cart = await store.GetCartAsync(User);

            Assert.All(cart.Items, i => Assert.True(i.Quantity > 0, $"quantity wrapped around to {i.Quantity}"));
        }

        [Fact, Trait("TC", "TC-DAT-12")]
        public async Task TC_DAT_12_AddItem_NullUserId_ShouldBeRejectedAsInvalidArgument()
        {
            var ex = await Assert.ThrowsAsync<RpcException>(() => NewStore().AddItemAsync(null, "p1", 1));
            Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-21")]
        public async Task TC_DAT_21_GetCart_AfterEmptyCart_ShouldKeepTheUserId()
        {
            var store = NewStore();
            await store.AddItemAsync(User, "p1", 1);
            await store.EmptyCartAsync(User);

            var cart = await store.GetCartAsync(User);

            Assert.Equal(User, cart.UserId);
        }

        [Fact, Trait("TC", "TC-DAT-28")]
        public async Task TC_DAT_28_AddItem_RequestWithoutItem_ShouldBeRejectedAsInvalidArgument()
        {
            var handler = new CartHandler(Substitute.For<ICartStore>());

            var ex = await Assert.ThrowsAsync<RpcException>(
                () => handler.AddItem(new AddItemRequest { UserId = "u1" }, null));

            Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
        }
    }
}
