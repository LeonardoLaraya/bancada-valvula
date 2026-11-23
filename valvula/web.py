from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .config import Invalid
from .control import Conflict


def create_app(bench):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=2048, TRUSTED_HOSTS=["127.0.0.1", "localhost"])

    def body(*fields):
        data = request.get_json()
        if not isinstance(data, dict) or set(data) != set(fields):
            raise Invalid("Campos da requisição inválidos.")
        for key in ("client", "epoch"):
            if key in data and (not isinstance(data[key], str) or not 1 <= len(data[key]) <= 64):
                raise Invalid("Identificador inválido.")
        return data

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", mock=bench.snapshot()["mock"])

    @app.get("/api/state")
    def state():
        return bench.snapshot()

    @app.post("/api/heartbeat")
    def heartbeat():
        bench.heartbeat(body("client")["client"])
        return state()

    @app.post("/api/apply")
    def apply():
        data = body("percent", "client", "epoch")
        bench.apply(data["percent"], data["client"], data["epoch"])
        return state()

    @app.post("/api/stop")
    def stop():
        body()
        bench.stop("Parada solicitada pela interface.")
        return state()

    @app.post("/api/calibration")
    def calibration():
        bench.calibrate(body("max_voltage")["max_voltage"])
        return state()

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error="Requisição HTTP inválida."), exc.code
        if isinstance(exc, (Invalid, Conflict)):
            return jsonify(error=str(exc)), 400 if isinstance(exc, Invalid) else 409
        app.logger.exception("Falha no backend")
        bench.stop(f"Falha no backend: {exc}", fault=True)
        return jsonify(error="Falha no backend. Confira os eventos da parada."), 500

    return app
