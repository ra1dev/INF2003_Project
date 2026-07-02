# Route handlers for the predictions pages.
from flask import Blueprint

from Backend.repositories.predictions_repository import predictions as render_predictions

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/predictions")
def predictions():
    return render_predictions()
