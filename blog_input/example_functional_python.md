---
title: Python Functional Programming Example
author: Akshay Badola
date: 2020-06-09
category: programming
keywords: python, functional programming
tags: python, functional programming, ref-man, arxiv, research
---

`<h1 align="center">A Python Functional Programming Example</h1>`{=html}

So I was working on my [ref-man](https://github.com/akshaybadola/ref-man) emacs
package and I had made some additions which incorporate a local python flask
server running on it which fetches data from from [dblp
API](https://dblp.uni-trier.de), [arXiv API](https://arxiv.org/help/api/) and
also I'm adding [semantic scholar](https://api.semanticscholar.org)
support. Originally there was only dblp calls so I had to modify the functions
and I took a functional programming approach, by generating partial functions
and using them to modify the existing code as I modified my existing
implementation.

The old dblp function was `dblp_old` which is still in the file

```python
def dblp_old():
    # checking request
    if not isinstance(request.json, str):
        data = request.json
    else:
        try:
            data = json.loads(request.json)
        except Exception:
            return json.dumps("BAD REQUEST")
    j = 0
    content = {}

    # The requests are fetched in parallel in batches which can be configured
    while True:
        _data = data[(args.batch_size * j): (args.batch_size * (j + 1))].copy()
        for k, v in content.items():
            if v == ["ERROR"]:
                _data.append(k)
        if not _data:
            break
        q = Queue()
        threads = []
        for d in _data:
            threads.append(Thread(target=dblp_fetch, args=[d, q],
                                  kwargs={"verbose": args.verbose}))
            threads[-1].start()
        for t in threads:
            t.join()
        content.update(_dblp_helper_old(q))
        j += 1
    return json.dumps(content)
```

So a function `dblp_fetch` is given to the threads with the data and a queue as
`args`. All it'll do is push responses to HTTP requests on to the queue and a
helper function `_helper` will process the results after fetching from the queue.

```python
def _helper(q):
    content = {}
    while not q.empty():
        query, response = q.get()
        if response.status_code == 200:
            result = json.loads(response.content)["result"]
            if result and "hits" in result and "hit" in result["hits"]:
                content[query] = []
                for hit in result["hits"]["hit"]:
                    info = hit["info"]
                    authors = info["authors"]["author"]
                    if isinstance(authors, list):
                        info["authors"] = [x["text"] for x in info["authors"]["author"]]
                    else:
                        info["authors"] = [authors["text"]]
                    content[query].append(info)
            else:
                content[query] = ["NO_RESULT"]
        elif response.status_code == 422:
            content[query] = ["NO_RESULT"]
        else:
            content[query] = ["ERROR"]
    return content
```

Fairly simple as you can see, but now if I want to add more APIs, I either write
separate `_fetch` and `_helper` functions for each of them or modify the
existing interface. Adding new functions is easier and hackier but error prone
in the long run because:

1. You'll end up copy pasting the code which will lead to errors
2. Changes in the implementation where that code interacts with the server will
   have to be replicated across
   
So I changed the functions in three ways:

1. Removed the multithreaded part so that the functions is executed parallely
   and responses handled by `_helper` for arbitrary functions.  I could have
   used a threadpool or processpool
   ([See](https://docs.python.org/3/library/concurrent.futures.html)), but I
   already had the threads implementation and it was working fine.
2. `q_helper` now takes three functions as parameters in addition to the queue

    ```python
    def q_helper(func_success, func_no_result, func_error, q):
        content = {}
        while not q.empty():
            query, response = q.get()
            if response.status_code == 200:
                func_success(query, response, content)
            elif response.status_code == 422:
                func_no_result(query, response, content)
            else:
                func_error(query, response, content)
        return content
    ```

    So it's entirely indpendent of whether we fetch from dblp or arxiv or any
    other source. It doesn't even handle any of the responses itself but passes
    them on to the functions. Data is shared with the `dict` `content`.  But
    that leaves us with a tiny problem: the `helper` function in
    `post_json_wrapper` only takes the `q` as an argument while our new
    `q_helper` requires 3 functions _and_ the `q`.
3. Now there are two ways to handle that: we can either pass all the functions
   to the `post_json_wrapper` or pass a new function which already has the three
   functions set. After all there will be a separate helper for each API. So
   this is where the final piece of the functional puzzle falls in.

   ```python
   _dblp_helper = partial(q_helper, _dblp_success, _dblp_no_result, _dblp_error)
   ```
   what we're doing is defining a new function composed of existing functions
   `q_helper`, `_dblp_success` etc.  but with everything but the `q` already
   set. `arxiv_helper` is defined similarly and results in fewer paramters being
   sent to `post_json_wrapper` which is _almost always_ a good thing.
   See [functools](https://docs.python.org/3/library/functools.html) module for
   information about `partial`.

So we've moved from an API specific threaded function and helper to an API
agnostic one while still keeping the original ideas of the implementation
intact! Pretty neat! I might write about how functional programming can help
reduce software complexity in another post, as even though it looks complex you
should keep in mind that most of the functions are stateless. They don't change
over time. That leaves us with fewer things to worry about.
