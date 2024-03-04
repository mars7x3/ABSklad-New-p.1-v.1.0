import logging

logger = logging.getLogger("mongo_logger.request")


class RequestMiddleware:

    @staticmethod
    def process_request(request):
        logger.info(request.__dict__)
