<h1>Cubanman</h1>

<h2>A web-tool aiming to help you monitor, and anonimyze your browsing, bypass any geographical-restrictions, create a flexible client/server</h2>

<h3>Functionalities</h3>

- Client mode
- Server mode
- Encryption
- Types of buffer (static, fixed)
- HTTP/1.1 proxy mode (Works but needs to be faster.)
- HTTP/2 proxy mode (not yet)
- HTTP/3 proxy mode (not yet)

<h3>Notes on Last Update</h3>

<h4>05/26/2025</h4>

- Proxy mode was added (Works using select module, maybe threads would be better)
- A timeout is being used to make the recv-proxy-sock loop end

<h4>Next Update</h4>

- Get rid of the timeout in proxy-socket recv and start evaluating response Content-Length headers, Also check if chunked data transfer is being used in order to handle it correctly.

<h3>Credits</h3>

- Giafranco Mendoza // creator
