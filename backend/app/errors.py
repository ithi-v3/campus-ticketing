from flask import jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .extensions import db


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error=err.message), err.status

    @app.errorhandler(IntegrityError)
    def handle_integrity(err):
        db.session.rollback()
        app.logger.warning("integrity error: %s", err.orig)
        return jsonify(error="That conflicts with existing data (duplicate or invalid reference)."), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_db(err):
        db.session.rollback()
        app.logger.exception("database error")
        return jsonify(error="Database error. Please try again."), 500

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify(error=err.description), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        app.logger.exception("unhandled error")
        return jsonify(error="Something went wrong on our side."), 500
