from flask import Blueprint, flash, redirect, render_template, request, url_for
from psycopg2 import Error as PostgresError

from Backend.db_conn import get_db
from Backend.repositories.favorites_repository import (
    create_favorite_player,
    create_favorite_team,
    delete_favorite_player,
    delete_favorite_team,
    get_favorite_player,
    get_favorite_team,
    list_favorite_players,
    list_favorite_teams,
    list_player_options,
    list_team_options,
    player_exists,
    team_exists,
    update_favorite_player,
    update_favorite_team,
)


favorites_bp = Blueprint("favorites", __name__, url_prefix="/favorites")


def parse_positive_int(raw_value, field_name):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a number."
    if value < 1:
        return None, f"{field_name} must be greater than zero."
    return value, None


@favorites_bp.route("")
def favorites():
    try:
        favorite_players = list_favorite_players()
        favorite_teams = list_favorite_teams()
        error_message = None
    except PostgresError as exc:
        get_db().rollback()
        favorite_players = []
        favorite_teams = []
        error_message = f"Favorites are unavailable: {exc}"

    return render_template(
        "favorites.html",
        title="Favorites",
        favorite_players=favorite_players,
        favorite_teams=favorite_teams,
        error_message=error_message,
    )


@favorites_bp.route("/players/new", methods=["GET", "POST"])
def new_favorite_player():
    if request.method == "POST":
        player_id, error = parse_positive_int(request.form.get("player_id"), "Player")
        notes = request.form.get("notes", "").strip()
        try:
            if error:
                flash(error, "error")
            elif not player_exists(player_id):
                flash("The selected player does not exist.", "error")
            else:
                favorite_id = create_favorite_player(player_id, notes)
                if favorite_id is None:
                    flash("That player is already in your favorites.", "error")
                else:
                    flash("Favorite player added successfully.", "success")
                    return redirect(url_for("favorites.favorites"))
        except PostgresError as exc:
            get_db().rollback()
            flash(f"Could not add favorite player: {exc}", "error")

    try:
        players = list_player_options()
    except PostgresError as exc:
        get_db().rollback()
        players = []
        flash(f"Could not load players: {exc}", "error")

    return render_template(
        "favorite_player_form.html",
        title="New Favorite Player",
        favorite=None,
        players=players,
    )


@favorites_bp.route("/teams/new", methods=["GET", "POST"])
def new_favorite_team():
    if request.method == "POST":
        team_id, error = parse_positive_int(request.form.get("team_id"), "Team")
        notes = request.form.get("notes", "").strip()
        try:
            if error:
                flash(error, "error")
            elif not team_exists(team_id):
                flash("The selected team does not exist.", "error")
            else:
                favorite_team_id = create_favorite_team(team_id, notes)
                if favorite_team_id is None:
                    flash("That team is already in your favorites.", "error")
                else:
                    flash("Favorite team added successfully.", "success")
                    return redirect(url_for("favorites.favorites"))
        except PostgresError as exc:
            get_db().rollback()
            flash(f"Could not add favorite team: {exc}", "error")

    try:
        teams = list_team_options()
    except PostgresError as exc:
        get_db().rollback()
        teams = []
        flash(f"Could not load teams: {exc}", "error")

    return render_template(
        "favorite_team_form.html",
        title="New Favorite Team",
        favorite=None,
        teams=teams,
    )


@favorites_bp.post("/players/<int:player_id>")
def add_player_from_list(player_id):
    try:
        if not player_exists(player_id):
            flash("The selected player does not exist.", "error")
        elif create_favorite_player(player_id) is None:
            flash("That player is already in your favorites.", "error")
        else:
            flash("Favorite player added successfully.", "success")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not add favorite player: {exc}", "error")
    return redirect(request.referrer or url_for("players.players_page"))


@favorites_bp.post("/teams/<int:team_id>")
def add_team_from_list(team_id):
    try:
        if not team_exists(team_id):
            flash("The selected team does not exist.", "error")
        elif create_favorite_team(team_id) is None:
            flash("That team is already in your favorites.", "error")
        else:
            flash("Favorite team added successfully.", "success")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not add favorite team: {exc}", "error")
    return redirect(request.referrer or url_for("teams.teams"))


@favorites_bp.route("/players/<int:favorite_id>/edit", methods=["GET", "POST"])
def edit_favorite_player(favorite_id):
    try:
        favorite = get_favorite_player(favorite_id)
        if favorite is None:
            flash("Favorite player not found.", "error")
            return redirect(url_for("favorites.favorites"))

        if request.method == "POST":
            notes = request.form.get("notes", "").strip()
            update_favorite_player(favorite_id, notes)
            flash("Favorite player updated successfully.", "success")
            return redirect(url_for("favorites.favorites"))
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not update favorite player: {exc}", "error")
        return redirect(url_for("favorites.favorites"))

    return render_template(
        "favorite_player_form.html",
        title="Edit Favorite Player",
        favorite=favorite,
        players=[],
    )


@favorites_bp.route("/teams/<int:favorite_team_id>/edit", methods=["GET", "POST"])
def edit_favorite_team(favorite_team_id):
    try:
        favorite = get_favorite_team(favorite_team_id)
        if favorite is None:
            flash("Favorite team not found.", "error")
            return redirect(url_for("favorites.favorites"))

        if request.method == "POST":
            notes = request.form.get("notes", "").strip()
            update_favorite_team(favorite_team_id, notes)
            flash("Favorite team updated successfully.", "success")
            return redirect(url_for("favorites.favorites"))
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not update favorite team: {exc}", "error")
        return redirect(url_for("favorites.favorites"))

    return render_template(
        "favorite_team_form.html",
        title="Edit Favorite Team",
        favorite=favorite,
        teams=[],
    )


@favorites_bp.post("/players/<int:favorite_id>/delete")
def remove_favorite_player(favorite_id):
    try:
        if delete_favorite_player(favorite_id):
            flash("Favorite player deleted successfully.", "success")
        else:
            flash("Favorite player not found.", "error")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not delete favorite player: {exc}", "error")
    return redirect(url_for("favorites.favorites"))


@favorites_bp.post("/teams/<int:favorite_team_id>/delete")
def remove_favorite_team(favorite_team_id):
    try:
        if delete_favorite_team(favorite_team_id):
            flash("Favorite team deleted successfully.", "success")
        else:
            flash("Favorite team not found.", "error")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not delete favorite team: {exc}", "error")
    return redirect(url_for("favorites.favorites"))
