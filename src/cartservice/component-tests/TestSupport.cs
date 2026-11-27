using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Hipstershop;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Options;
using NSubstitute;

namespace cartservice.componenttests
{
    /// <summary>
    /// Test doubles shared by the suites. None of them touches a network, a clock or a disk.
    /// </summary>
    internal static class TestSupport
    {
        /// <summary>FAKE: a working, in-memory IDistributedCache (stands in for Redis).</summary>
        public static IDistributedCache NewFakeCache() =>
            new MemoryDistributedCache(Options.Create(new MemoryDistributedCacheOptions()));

        /// <summary>STUB: every read fails, as if the cache server were down.</summary>
        public static IDistributedCache CacheFailingOnGet()
        {
            var cache = Substitute.For<IDistributedCache>();
            cache.GetAsync(Arg.Any<string>(), Arg.Any<CancellationToken>())
                 .Returns(Task.FromException<byte[]>(new InvalidOperationException("cache down")));
            return cache;
        }

        /// <summary>STUB: reads find nothing, every write fails.</summary>
        public static IDistributedCache CacheFailingOnSet()
        {
            var cache = Substitute.For<IDistributedCache>();
            // NSubstitute would auto-return an empty array; the contract needs "key not found" = null.
            cache.GetAsync(Arg.Any<string>(), Arg.Any<CancellationToken>())
                 .Returns(Task.FromResult<byte[]>(null));
            cache.SetAsync(Arg.Any<string>(), Arg.Any<byte[]>(),
                           Arg.Any<DistributedCacheEntryOptions>(), Arg.Any<CancellationToken>())
                 .Returns(Task.FromException(new InvalidOperationException("cache down")));
            return cache;
        }

        /// <summary>FAKE seeded with bytes that are not a serialized Cart.</summary>
        public static async Task<IDistributedCache> CacheWithCorruptCart(string userId)
        {
            var cache = NewFakeCache();
            await cache.SetAsync(userId, new byte[] { 0xFF, 0xFF, 0xFF });
            return cache;
        }

        public static int QuantityOf(Cart cart, string productId) =>
            cart.Items.Single(i => i.ProductId == productId).Quantity;
    }
}
