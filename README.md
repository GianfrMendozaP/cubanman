<h1>Cubanman</h1>

<h2>A web-tool aiming to help you monitor, and anonimyze your browsing, bypass any geographical-restrictions, create a flexible client/server</h2>

<h3>Functionalities</h3>

- Client mode
- Server mode
- Encryption
- Types of buffer (static, fixed)
- HTTP and HTTPS proxy mode

<h3>Notes on Last Update</h3>

<h4>11/24/2025</h4>

- Now an x argument can be given when using proxy in order to set a thread limit, this way we can pass -1 for unlimited threads, 0 for only EPOLL, or any positive number major than 3 for mixed (threads and EPOLL). It has to be major than 3 because theres a logging thread, a threadCleaner thread, and obviously the main thread

<h4>Next Update</h4>

- Optimize http 2.0 support
- Add separate logging for each thread

<h3>Credits</h3>

- Giafranco Mendoza // Dev
