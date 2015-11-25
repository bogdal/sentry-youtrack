FROM sentry

USER root
RUN pip install sentry==7.7.4
ADD entrypoint.sh /entrypoint.sh

USER user
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sentry", "start"]
