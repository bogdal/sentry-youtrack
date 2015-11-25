Docker Compose
--------------
Preparation of test environment:

**Sentry**::

    $ cd sentry
    $ docker-compose build
    $ docker-compose run sentry sentry syncdb
    $ docker-compose run sentry sentry migrate
    $ docker-compose up -d

``sentry`` is configured to listen on port ``9000``.

**YouTrack**::

    $ cd youtrack
    $ docker-compose up -d

``youtrack`` is configured to listen on ports ``80`` and ``443``.

Plugin configuration
--------------------

``YouTrack`` instance urls that link the above containers:

  - http://my.youtrack
  - https://ssl.youtrack
