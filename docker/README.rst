Docker Compose
--------------
Preparation of test environment::

    $ docker-compose build
    $ docker-compose run sentry sentry syncdb
    $ docker-compose run sentry sentry migrate
    $ docker-compose up -d

``Sentry`` is configured to listen on port ``9000``. ``YouTrack`` is configured to listen on ports ``80`` and ``443``.

Plugin configuration
--------------------

``YouTrack`` instance urls for ``sentry``:

  - http://my.youtrack
  - https://ssl.youtrack
