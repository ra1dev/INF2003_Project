from flask import Blueprint

from Backend.repositories.nosql_repository import event_search as render_event_search
from Backend.repositories.nosql_repository import nosql_insights as render_nosql_insights

nosql_bp = Blueprint("nosql", __name__)


@nosql_bp.route("/nosql-insights")
def nosql_insights():
    return render_nosql_insights()


@nosql_bp.route("/event-search")
def event_search():
    return render_event_search()
