---
title: Sending Mail with Python and Googleapi for Emacs
author: Akshay Badola
date: 2020-12-01
category: emacs
keywords: emacs, mu4e, emacs-lisp, python, mail, gmail
tags: emacs, mail, python, lisp
---

`<h1 align="center">Sending Mail with Python and Googleapi for Emacs</h1>`{=html}

So I love Emacs. Why I love it would be the subject of another blog post, but as
I love it I want to do everything from it, including sending and reading mail as
it is very convenient for me. Emacs can automate a lot of tasks for me.

Anyway so [mu4e](https://www.djcbsoftware.nl/code/mu/) does a really good job of
indexing and reading mails in emacs. It has a good compose feature also and it
leaves receiving and sending mail up to the mail client of user's choice.

For receiving mail I've been using [offlineimap](http://www.offlineimap.org/)
which also does a fairly good job. It's not fussy and works as expected. The
problem I faced is with sending mail. [offlineimap](http://www.offlineimap.org/)
can work with
[xoauth2](https://developers.google.com/gmail/imap/xoauth2-protocol) (xoauth2 is
a variant of Oauth with some custom extensions by Google) and I have indeed
retrieved and stored tokens for it which it can use to fetch my mail. And
earlier I was using Emacs's `smtpmail-send-it` to send mail. The problem occurs
with the `auth-source`, the backend Emacs uses to authenticate with any server.

Now I did find this
[auth-source-xoauth2](https://github.com/ccrusius/auth-source-xoauth2) and it
works fine actually, but...and it's a very annoying but, sometimes
`smtpmail-send-it` does not authenticate and gives me a `334` error
(authentication required). And it happens often enough for me to get irked.

So the solution? One solution would be to use [postfix](http://www.postfix.org/)
to send mail and actually I did install [postfix](http://www.postfix.org/) to
see if I could configure Emacs for it, but it proved to be overkill for my
use. It's supposed to be a general purpose mail server and there are too many
configurations and plugins for my simple use case.

So after a bunch of research (at which I'm fairly good) and hacking, I
discovered that google has fairly good python library
[https://github.com/googleapis/google-api-python-client] with a fairly extensive
set of features. And sending mail from it is not that difficult and decided to
write a simple server which can send mail instead of `smtpmail-send-it`.

What it does basically is given a mail message in a proper format with all
correct fields and boundaries, it reads the credentials from a [password
store](https://www.passwordstore.org/), stored as a JSON formatted string and
initiates a `service` instance. From that we can send and receive mail messages,
and we only need the send part of that.

I've made it a [flask](https://flask.palletsprojects.com/) server so it only
needs to read the credentials once from the store at startup, so I don't need to
feed them again after the timeout expires to emacs in case I need to send the
mail later. You can take a look at it
[here](https://gist.github.com/akshaybadola/cb41f5e8a4bde80dd9d5d191d4afd41f).

OK, fine you ask, but who'll format the message and attachments and insert
proper fields? Why, Emacs of course! Instead of launching a network process, we
simply send to `gmailer` instead. I've posted that function as a gist
[here](https://gist.github.com/akshaybadola/862c01471f899afdc7a8970de1b5052c).

Basically, [mu4e](https://www.djcbsoftware.nl/code/mu/) and `smtpmail` do all
the hard work and we steal the final product and dump it to the google client!
Problemm solved (for now, until the bugs come :-D). I'm sure there'll be bugs, but
I'll keep maintaining the gists and if required gather them into a repo. Happy
Emacs'ing!
