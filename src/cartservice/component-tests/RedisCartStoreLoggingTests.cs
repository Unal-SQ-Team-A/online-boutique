using System;
using System.IO;
using System.Threading.Tasks;
using cartservice.cartstore;
using Xunit;
using static cartservice.componenttests.TestSupport;

namespace cartservice.componenttests
{
    /// <summary>Operational observability: each store operation logs its call with the arguments.</summary>
    [Collection("console")]
    public class RedisCartStoreLoggingTests
    {
        private static async Task<string> CaptureAsync(Func<Task> action)
        {
            var original = Console.Out;
            var writer = new StringWriter();
            Console.SetOut(writer);
            try { await action(); }
            finally { Console.SetOut(original); }
            return writer.ToString();
        }

        [Fact, Trait("TC", "TC-DAT-39")]
        public async Task AddItem_LogsUserProductAndQuantity()
        {
            var store = new RedisCartStore(NewFakeCache());
            var log = await CaptureAsync(() => store.AddItemAsync("u-log", "p-log", 7));
            Assert.Contains("AddItemAsync called with userId=u-log, productId=p-log, quantity=7", log);
        }

        [Fact, Trait("TC", "TC-DAT-40")]
        public async Task EmptyCart_LogsUser()
        {
            var store = new RedisCartStore(NewFakeCache());
            var log = await CaptureAsync(() => store.EmptyCartAsync("u-log"));
            Assert.Contains("EmptyCartAsync called with userId=u-log", log);
        }

        [Fact, Trait("TC", "TC-DAT-41")]
        public async Task GetCart_LogsUser()
        {
            var store = new RedisCartStore(NewFakeCache());
            var log = await CaptureAsync(() => store.GetCartAsync("u-log"));
            Assert.Contains("GetCartAsync called with userId=u-log", log);
        }
    }
}
