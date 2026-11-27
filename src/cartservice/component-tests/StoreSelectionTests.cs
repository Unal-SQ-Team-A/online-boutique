using System.Collections.Generic;
using System.Linq;
using cartservice.cartstore;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace cartservice.componenttests
{
    /// <summary>
    /// C-DAT-3 store selection in Startup.ConfigureServices. DECISION TABLE (one rule per row).
    /// The dependency IConfiguration is replaced by an in-memory configuration (stub).
    /// The registrations are inspected, never resolved: resolving Spanner/AlloyDB would open connections.
    /// Expected values come from the order of the if/else chain in Startup.cs (ASSUMPTION: no other spec exists).
    /// Empty string = variable not set. expectedCache "" = no IDistributedCache registered.
    /// </summary>
    public class StoreSelectionTests
    {
        //                tc            REDIS_ADDR     SPANNER_PROJECT  SPANNER_CONN  ALLOYDB_IP   expected store      expected cache
        [Theory, Trait("TC", "TC-DAT-31..38")]
        [InlineData("TC-DAT-31", "redis:6379", "",        "",   "",        "RedisCartStore",   "RedisCacheImpl")]
        [InlineData("TC-DAT-32", "",           "proj-1",  "",   "",        "SpannerCartStore", "")]
        [InlineData("TC-DAT-33", "",           "",        "cs", "",        "SpannerCartStore", "")]
        [InlineData("TC-DAT-34", "",           "",        "",   "10.0.0.5", "AlloyDBCartStore", "")]
        [InlineData("TC-DAT-35", "",           "",        "",   "",        "RedisCartStore",   "MemoryDistributedCache")]
        [InlineData("TC-DAT-36", "redis:6379", "proj-1",  "",   "",        "RedisCartStore",   "RedisCacheImpl")]
        [InlineData("TC-DAT-37", "",           "proj-1",  "",   "10.0.0.5", "SpannerCartStore", "")]
        [InlineData("TC-DAT-38", "redis:6379", "proj-1",  "cs", "10.0.0.5", "RedisCartStore",   "RedisCacheImpl")]
        public void StoreSelection_FollowsDecisionTable(
            string tc, string redis, string spannerProject, string spannerConnection, string alloyDb,
            string expectedStore, string expectedCache)
        {
            Assert.StartsWith("TC-DAT-", tc); // the rule id travels in the verdict line of each row
            var configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string>
                {
                    ["REDIS_ADDR"] = redis,
                    ["SPANNER_PROJECT"] = spannerProject,
                    ["SPANNER_CONNECTION_STRING"] = spannerConnection,
                    ["ALLOYDB_PRIMARY_IP"] = alloyDb,
                })
                .Build();
            var services = new ServiceCollection();

            new Startup(configuration).ConfigureServices(services);

            var store = Assert.Single(services, d => d.ServiceType == typeof(ICartStore));
            Assert.Equal(expectedStore, store.ImplementationType.Name);
            var cache = services.SingleOrDefault(d => d.ServiceType == typeof(IDistributedCache));
            Assert.Equal(expectedCache, cache?.ImplementationType?.Name ?? "");
        }
    }
}
