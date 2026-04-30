# How to Verify HTTP Caching Works in Routes

> First, call the route. Here are two examples:
>
>    curl.exe -v http://localhost:8000/api/v1/tea_profiles/24
>    curl.exe -v "http://localhost:8000/api/v1/tea_profiles?limit=10&offset=0"
>    
> This should produce some information. Copy the "etag" and "last-modified". 
>
>    1. To test the Etag, do
>
>	    curl.exe -v http://localhost:8000/api/v1/tea_profiles/24 ^ -H "If-None-Match: [etag]"
>	    curl.exe -v "http://localhost:8000/api/v1/tea_profiles?limit=10&offset=0" -H "If-None-Match: [etag]"
>
>    You should get: 
>
>	    HTTP/1.1 304 Not Modified
>	
>    2. To test Last-Modified, do 
>
>    	curl.exe -v http://localhost:8000/api/v1/tea_profiles/24 ^ -H "If-Modified-Since: [last-modified]"
>    	curl.exe -v "http://localhost:8000/api/v1/tea_profiles?limit=10&offset=0" -H "If-Modified-Since: [last-modified]"
>	
>    You should get:
>
>    	HTTP/1.1 304 Not Modified
>	
>    3. To test that a new request returns 200 Ok, remove the headers:
>
>    	curl.exe -v http://localhost:8000/api/v1/tea_profiles/24
>    	curl.exe -v "http://localhost:8000/api/v1/tea_profiles?limit=10&offset=0"
>	
>    4. If you repeat the headless curl after the 300 seconds (5 minutes), you should get a new ETag, Last-Modified, and fresh DB fetch.
>
>    Ex: If our initial call 
>
>        curl.exe -v http://localhost:8000/api/v1/tea_profiles/24
>
>    yields
>
>    	etag: dea51a2ce1dcd054db3745ed6f6e2918
>    	last-modified: Wed, 29 Apr 2026 22:06:20 GMT
>
>    Then we would do:
>
>    	curl.exe -v http://localhost:8000/api/v1/tea_profiles/24 ^ -H "If-None-Match: dea51a2ce1dcd054db3745ed6f6e2918"
>    	curl.exe -v http://localhost:8000/api/v1/tea_profiles/24 ^ -H "If-Modified-Since: Wed, 29 Apr 2026 22:06:20 GMT"
>
> To quickly confirm that caching is working without using curl, you can test using your browser. Hit a route that uses caching. Ex:
> 
>     http://localhost:8000/api/v1/tea_profiles
> 
> This should populate the cache with the tea_profiles response. Check the cache state by visiting:
> 
>     http://localhost:8000/debug/cache
>
> You should see something like:
> 
>     {
>      "hits": 0,
>       "misses": 1,
>       "keys": [
>         {
>           "key": "tea_profiles:list:{}:100:0",
>           "ttl_remaining": 298,
>           "timestamp": "2026-04-30T16:02:44Z"
>         }
>       ]
>     }
> Hit the same route again:
> 
>     http://localhost:8000/api/v1/tea_profiles
>
> This should be a cache hit. Refresh the debug endpoint:
>
>     http://localhost:8000/debug/cache
> 
> The hits counter should increment. This gives us a quick, visual confirmation that:
> 
>     values are being cached
>     TTL is decreasing
>     hits/misses are tracked
>     the debug endpoint is wired correctly
