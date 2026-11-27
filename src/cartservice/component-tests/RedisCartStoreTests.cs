using System.Linq;
using System.Threading.Tasks;
using cartservice.cartstore;
using Grpc.Core;
using Hipstershop;
using Xunit;
using static cartservice.componenttests.TestSupport;

namespace cartservice.componenttests
{
    /// <summary>
    /// C-DAT-1 RedisCartStore. Dependency IDistributedCache replaced by a fake (state) or a stub (failures).
    /// Cases TC-DAT-01..21 are derived from the contract (see the component sheet), not from the code.
    /// </summary>
    public class RedisCartStoreTests
    {
        private const string User = "user-1";

        private static RedisCartStore NewStore() => new RedisCartStore(NewFakeCache());

        // ---- Equivalence partitioning ------------------------------------------------------

        [Fact, Trait("TC", "TC-DAT-01")]
        public async Task TC_DAT_01_AddItem_UserWithoutCart_CreatesCartWithThatItem()
        {
            var store = NewStore();

            await store.AddItemAsync(User, "p1", 2);

            var cart = await store.GetCartAsync(User);
            Assert.Equal(User, cart.UserId);
            Assert.Single(cart.Items);
            Assert.Equal("p1", cart.Items[0].ProductId);
            Assert.Equal(2, cart.Items[0].Quantity);
        }

        [Fact, Trait("TC", "TC-DAT-02")]
        public async Task TC_DAT_02_AddItem_DifferentProduct_AppendsSecondItem()
        {
            var store = NewStore();
            await store.AddItemAsync(User, "p1", 1);

            await store.AddItemAsync(User, "p2", 4);

            var cart = await store.GetCartAsync(User);
            Assert.Equal(2, cart.Items.Count);
            Assert.Equal(1, QuantityOf(cart, "p1"));
            Assert.Equal(4, QuantityOf(cart, "p2"));
        }

        [Fact, Trait("TC", "TC-DAT-03")]
        public async Task TC_DAT_03_AddItem_SameProduct_SumsQuantityAndKeepsSingleItem()
        {
            var store = NewStore();
            await store.AddItemAsync(User, "p1", 2);

            await store.AddItemAsync(User, "p1", 3);

            var cart = await store.GetCartAsync(User);
            Assert.Single(cart.Items);
            Assert.Equal(5, cart.Items[0].Quantity);
        }

        [Fact, Trait("TC", "TC-DAT-04")]
        public async Task TC_DAT_04_GetCart_UnknownUser_ReturnsEmptyCart()
        {
            var store = NewStore();

            var cart = await store.GetCartAsync("nobody");

            Assert.Empty(cart.Items);
            Assert.Equal(new Cart(), cart);
        }

        [Fact, Trait("TC", "TC-DAT-05")]
        public async Task TC_DAT_05_AddItem_TwoUsers_CartsAreIndependent()
        {
            var store = NewStore();

            await store.AddItemAsync("alice", "p1", 1);
            await store.AddItemAsync("bob", "p2", 7);

            var alice = await store.GetCartAsync("alice");
            var bob = await store.GetCartAsync("bob");
            Assert.Equal("p1", Assert.Single(alice.Items).ProductId);
            Assert.Equal("p2", Assert.Single(bob.Items).ProductId);
            Assert.Equal(7, bob.Items[0].Quantity);
        }

        [Fact, Trait("TC", "TC-DAT-06")]
        public async Task TC_DAT_06_EmptyCart_AfterAddItem_LeavesNoItems()
        {
            var store = NewStore();
            await store.AddItemAsync(User, "p1", 2);

            await store.EmptyCartAsync(User);

            Assert.Empty((await store.GetCartAsync(User)).Items);
        }

        [Fact, Trait("TC", "TC-DAT-07")]
        public async Task TC_DAT_07_EmptyCart_UnknownUser_DoesNotFailAndStaysEmpty()
        {
            var store = NewStore();

            await store.EmptyCartAsync("nobody");

            Assert.Empty((await store.GetCartAsync("nobody")).Items);
        }

        // ---- Boundary values (quantity) ----------------------------------------------------

        [Fact, Trait("TC", "TC-DAT-08")]
        public async Task TC_DAT_08_AddItem_QuantityOne_LowerValidBoundary_IsStored()
        {
            var store = NewStore();

            await store.AddItemAsync(User, "p1", 1);

            Assert.Equal(1, QuantityOf(await store.GetCartAsync(User), "p1"));
        }

        // TC-DAT-09..12 (quantity 0, negative, overflow, null user) live in SuspectedDefectTests.cs

        // ---- Exceptional behavior (EXC-1): any cache failure becomes FailedPrecondition ----

        [Fact, Trait("TC", "TC-DAT-13")]
        public async Task TC_DAT_13_GetCart_CacheFails_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(CacheFailingOnGet());

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.GetCartAsync(User));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
        }

        [Fact, Trait("TC", "TC-DAT-14")]
        public async Task TC_DAT_14_AddItem_CacheReadFails_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(CacheFailingOnGet());

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.AddItemAsync(User, "p1", 1));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
            Assert.StartsWith("Can't access cart storage.", ex.Status.Detail);
            Assert.True(ex.Status.Detail.Length > "Can't access cart storage. ".Length);
        }

        [Fact, Trait("TC", "TC-DAT-15")]
        public async Task TC_DAT_15_AddItem_CacheWriteFails_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(CacheFailingOnSet());

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.AddItemAsync(User, "p1", 1));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
            Assert.StartsWith("Can't access cart storage.", ex.Status.Detail);
            Assert.True(ex.Status.Detail.Length > "Can't access cart storage. ".Length);
        }

        [Fact, Trait("TC", "TC-DAT-16")]
        public async Task TC_DAT_16_EmptyCart_CacheWriteFails_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(CacheFailingOnSet());

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.EmptyCartAsync(User));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
            Assert.StartsWith("Can't access cart storage.", ex.Status.Detail);
            Assert.True(ex.Status.Detail.Length > "Can't access cart storage. ".Length);
        }

        [Fact, Trait("TC", "TC-DAT-17")]
        public async Task TC_DAT_17_GetCart_CorruptStoredBytes_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(await CacheWithCorruptCart(User));

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.GetCartAsync(User));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
            Assert.StartsWith("Can't access cart storage.", ex.Status.Detail);
            Assert.True(ex.Status.Detail.Length > "Can't access cart storage. ".Length);
        }

        [Fact, Trait("TC", "TC-DAT-18")]
        public async Task TC_DAT_18_AddItem_CorruptStoredBytes_RaisesFailedPrecondition()
        {
            var store = new RedisCartStore(await CacheWithCorruptCart(User));

            var ex = await Assert.ThrowsAsync<RpcException>(() => store.AddItemAsync(User, "p1", 1));

            Assert.Equal(StatusCode.FailedPrecondition, ex.StatusCode);
            Assert.StartsWith("Can't access cart storage.", ex.Status.Detail);
            Assert.True(ex.Status.Detail.Length > "Can't access cart storage. ".Length);
        }

        // ---- Invariant (INV-1) -------------------------------------------------------------

        [Fact, Trait("TC", "TC-DAT-19")]
        public async Task TC_DAT_19_AnySequenceOfAddItem_NeverDuplicatesAProduct()
        {
            var store = NewStore();

            foreach (var product in new[] { "a", "b", "a", "c", "b", "a" })
                await store.AddItemAsync(User, product, 1);

            var cart = await store.GetCartAsync(User);
            Assert.Equal(3, cart.Items.Count);
            Assert.Equal(cart.Items.Count, cart.Items.Select(i => i.ProductId).Distinct().Count());
            Assert.Equal(6, cart.Items.Sum(i => i.Quantity));
        }

        // ---- Ping --------------------------------------------------------------------------

        [Fact, Trait("TC", "TC-DAT-20")]
        public void TC_DAT_20_Ping_ReturnsTrue()
        {
            Assert.True(NewStore().Ping());
        }
    }
}
