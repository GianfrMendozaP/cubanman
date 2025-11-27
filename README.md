<h1>Cubanman</h1>

<h2>A web-tool aiming to help you monitor, and anonimyze your browsing, bypass any geographical-restrictions, create a flexible client/server</h2>

<h3>Functionalities</h3>

- Client mode
- Server mode
- Encryption
- Types of buffer (static, fixed)
- HTTP and HTTPS proxy mode (Threads/Epoll/ThreadedEpoll)

<h3>Notes on Last Update</h3>

<h4>11/27/2025</h4>

- Now you cant put a limit on how many threads the proxy can create, instead you will have to choose between threaded mode or epoll mode.
- A "mixed" mode was added, it's called threadedEpoll. basically creates threads with all the sockets that returned EPOLLIN and waits for those threads to finish recving in order to join them and go on with the next epoll.poll() call
- A timeout argument was added into the argparser since the threaded mode sometimes depends on timeouts to know when a socket has finished its task

<h4>Next Update</h4>

- Maybe a graphic interface
- Add separate logging for each thread
- refactor part of the code

<h3>Credits</h3>

- Giafranco Mendoza // Dev
