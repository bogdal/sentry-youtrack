FROM sentry:7.7

USER root
RUN pip install kombu==3.0.30
ADD entrypoint.sh /entrypoint.sh

USER user
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sentry", "start"]
