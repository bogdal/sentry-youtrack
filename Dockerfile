FROM sentry

USER root

RUN pip install -U sentry

RUN git clone https://github.com/bogdal/sentry-youtrack /plugin
RUN cd /plugin && python setup.py develop

USER user
