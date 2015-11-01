sentry-youtrack
===============

.. image:: https://travis-ci.org/bogdal/sentry-youtrack.png?branch=develop   
    :target: https://travis-ci.org/bogdal/sentry-youtrack

.. image:: https://version-image.appspot.com/pypi/?name=sentry-youtrack
    :target: https://pypi.python.org/pypi/sentry-youtrack

A Sentry plugin which creates YouTrack issues from sentry events and allows to assign an existing YouTrack issues to sentry event groups.

Install
-------

Install the package via ``pip``::

    pip install sentry-youtrack

Configuration
-------------
Go to your project's configuration page (Projects -> [Project]) and select the YouTrack tab. 
Enter the required credentials and save changes. Filling out the form is a two-step process
(one to fill in credentials, one to configure project).

Screenshots
-----------

.. image:: https://github-bogdal.s3.amazonaws.com/sentry-youtrack/new_issue.png
.. image:: https://github-bogdal.s3.amazonaws.com/sentry-youtrack/assign.png
