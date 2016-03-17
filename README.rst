sentry-youtrack
===============

.. image:: https://travis-ci.org/bogdal/sentry-youtrack.png?branch=master
    :target: https://travis-ci.org/bogdal/sentry-youtrack

.. image:: https://version-image.appspot.com/pypi/?name=sentry-youtrack
    :target: https://pypi.python.org/pypi/sentry-youtrack

A Sentry plugin which creates YouTrack issues from sentry events and allows to assign an existing YouTrack issues to sentry event groups.

Install
-------

Install the package via ``pip``::

    pip install sentry-youtrack

``sentry-youtrack >= 0.3.0`` supports **Sentry 8.x**.
``sentry-youtrack < 0.3.0`` supports **Sentry 7.x**.

Configuration
-------------
Go to your project's configuration page (Projects -> [Project]) and select the YouTrack tab.
Enter the required credentials and save changes. Filling out the form is a two-step process
(one to fill in credentials, one to configure project).

If you want to use ``YouTrack`` instance without valid ssl certificate add the following line to the ``sentry`` config file::

    YOUTRACK_VERIFY_SSL_CERTIFICATE = False


Screenshots
-----------

.. image:: https://github-bogdal.s3.amazonaws.com/sentry-youtrack/new_issue.png
.. image:: https://github-bogdal.s3.amazonaws.com/sentry-youtrack/assign.png

Docker Compose
--------------

See details `here <https://github.com/bogdal/sentry-youtrack/tree/master/docker/>`_.
