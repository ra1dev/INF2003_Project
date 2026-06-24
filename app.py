from flask import Flask

from Backend.db_conn import init_app
from Backend.routes.home import home_bp
from Backend.routes.insights import insights_bp
from Backend.routes.matches import matches_bp
from Backend.routes.nosql import nosql_bp
from Backend.routes.player_comparison import player_comparison_bp
from Backend.routes.players import players_bp
from Backend.routes.predictions import predictions_bp
from Backend.routes.season import season_bp
from Backend.routes.teams import teams_bp

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

init_app(app)

app.register_blueprint(home_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(players_bp)
app.register_blueprint(player_comparison_bp)
app.register_blueprint(teams_bp)
app.register_blueprint(matches_bp)
app.register_blueprint(predictions_bp)
app.register_blueprint(season_bp)
app.register_blueprint(nosql_bp)

if __name__ == "__main__":
    app.run(debug=True)
