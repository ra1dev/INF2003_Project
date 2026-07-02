# Route handlers for the admin CRUD and annotation workflow.
from bson.errors import InvalidId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from psycopg2 import Error as PostgresError
from pymongo.errors import PyMongoError

from Backend.db_conn import get_db
from Backend.repositories.admin_repository import (
    create_event_annotation,
    create_match_note,
    delete_event_annotation,
    delete_match_note,
    event_annotation_counts,
    event_coverage_seasons,
    event_covered_match_ids,
    get_event_annotation,
    get_match_note,
    get_source_match_event,
    list_event_annotations,
    list_filtered_matches,
    list_match_notes,
    list_match_options,
    list_note_filter_options,
    list_teams_for_season,
    match_exists,
    update_event_annotation,
    update_match_note,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def parse_positive_int(raw_value, field_name):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a number."
    if value < 1:
        return None, f"{field_name} must be greater than zero."
    return value, None


def match_note_form_data():
    match_id, error = parse_positive_int(request.form.get("match_id"), "Match")
    title = request.form.get("note_title", "").strip()
    content = request.form.get("note_content", "").strip()

    if error:
        return None, error
    if not title:
        return None, "Report title is required."
    if len(title) > 150:
        return None, "Report title must be 150 characters or fewer."
    if not content:
        return None, "Report content is required."
    if not match_exists(match_id):
        return None, "The selected match does not exist."
    return {"match_id": match_id, "note_title": title, "note_content": content}, None


def annotation_content_form_data():
    """Validate the user-authored, flexible part of an event annotation."""
    annotation = request.form.get("annotation", "").strip()
    if not annotation:
        return None, "Annotation is required."
    raw_tags = request.form.get("tags", "")
    tags = []
    for tag in raw_tags.split(","):
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in tags:
            tags.append(cleaned[:30])
    return {"annotation": annotation, "tags": tags[:10]}, None


@admin_bp.route("/match-notes")
def match_notes():
    season_name = request.args.get("season", "").strip()
    team_id = request.args.get("team_id", type=int)
    try:
        seasons, teams = list_note_filter_options()
        if not season_name and seasons:
            season_name = seasons[0]["season_name"]
        matches = list_filtered_matches(season_name, team_id) if season_name else []
        notes = list_match_notes(season_name=season_name, team_id=team_id)
        error_message = None
    except PostgresError as exc:
        get_db().rollback()
        seasons = []
        teams = []
        matches = []
        notes = []
        error_message = f"PostgreSQL match reports are unavailable: {exc}"
    return render_template(
        "admin_match_notes.html",
        title="PostgreSQL Match Reports",
        notes=notes,
        matches=matches,
        seasons=seasons,
        teams=teams,
        selected_season=season_name,
        selected_team_id=team_id,
        error_message=error_message,
    )


@admin_bp.post("/matches/<int:match_id>/notes")
def add_match_note_to_match(match_id):
    """Create a note directly from the selected match detail page."""
    try:
        title = request.form.get("note_title", "").strip()
        content = request.form.get("note_content", "").strip()
        if not match_exists(match_id):
            flash("The selected match does not exist.", "error")
            return redirect(url_for("admin.match_notes"))
        if not title or not content:
            flash("Report title and content are required.", "error")
        elif len(title) > 150:
            flash("Report title must be 150 characters or fewer.", "error")
        else:
            # CREATE: the match comes from the current detail page, not manual ID entry.
            create_match_note(match_id, title, content)
            flash("Match report created successfully.", "success")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not create match report: {exc}", "error")
    return redirect(url_for("matches.match_detail", match_id=match_id) + "#match-notes")


@admin_bp.route("/match-notes/new", methods=["GET", "POST"])
def new_match_note():
    if request.method == "POST":
        try:
            data, error = match_note_form_data()
            if error:
                flash(error, "error")
            else:
                # CREATE: INSERT the validated note into PostgreSQL.
                create_match_note(**data)
                flash("Match report created successfully.", "success")
                return redirect(url_for("admin.match_notes"))
        except PostgresError as exc:
            get_db().rollback()
            flash(f"Could not create match report: {exc}", "error")

    try:
        matches = list_match_options()
    except PostgresError as exc:
        get_db().rollback()
        matches = []
        flash(f"Could not load matches: {exc}", "error")
    return render_template(
        "admin_match_note_form.html",
        title="New Match Report",
        note=None,
        matches=matches,
    )


@admin_bp.route("/match-notes/<int:note_id>/edit", methods=["GET", "POST"])
def edit_match_note(note_id):
    try:
        note = get_match_note(note_id)
        if note is None:
            flash("Match report not found.", "error")
            return redirect(url_for("admin.match_notes"))

        if request.method == "POST":
            title = request.form.get("note_title", "").strip()
            content = request.form.get("note_content", "").strip()
            if not title or not content:
                flash("Report title and content are required.", "error")
            elif len(title) > 150:
                flash("Report title must be 150 characters or fewer.", "error")
            else:
                # UPDATE: parameterized UPDATE and updated_at refresh.
                update_match_note(note_id, title, content)
                flash("Match report updated successfully.", "success")
                return_match_id = request.args.get("return_to_match", type=int)
                if return_match_id:
                    return redirect(
                        url_for("matches.match_detail", match_id=return_match_id) + "#match-notes"
                    )
                return redirect(url_for("admin.match_notes"))
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not update match report: {exc}", "error")
        return redirect(url_for("admin.match_notes"))

    return render_template(
        "admin_match_note_form.html",
        title="Edit Match Report",
        note=note,
        matches=[],
        return_match_id=request.args.get("return_to_match", type=int),
    )


@admin_bp.post("/match-notes/<int:note_id>/delete")
def remove_match_note(note_id):
    return_match_id = request.form.get("return_to_match", type=int)
    try:
        # DELETE: parameterized DELETE by PostgreSQL primary key.
        if delete_match_note(note_id):
            flash("Match report deleted successfully.", "success")
        else:
            flash("Match report not found.", "error")
    except PostgresError as exc:
        get_db().rollback()
        flash(f"Could not delete match report: {exc}", "error")
    if return_match_id:
        return redirect(url_for("matches.match_detail", match_id=return_match_id) + "#match-notes")
    return redirect(url_for("admin.match_notes"))


@admin_bp.route("/event-annotations")
def event_annotations():
    season_name = ""
    team_id = request.args.get("team_id", type=int)
    error_message = None
    matches = []
    covered_seasons = set()
    try:
        seasons, teams = list_note_filter_options()
    except PostgresError as exc:
        get_db().rollback()
        seasons = []
        teams = []
        matches = []
        error_message = f"Match filters are unavailable: {exc}"

    try:
        covered_seasons = event_coverage_seasons()
        season_name = next(
            (
                season["season_name"]
                for season in seasons
                if season["season_name"] in covered_seasons
            ),
            "",
        )
        teams = list_teams_for_season(season_name) if season_name else []
        matches = list_filtered_matches(season_name, team_id) if season_name else []
        covered_match_ids = event_covered_match_ids(
            fixture["match_id"] for fixture in matches
        )
        matches = [
            fixture for fixture in matches
            if fixture["match_id"] in covered_match_ids
        ]
        match_ids = [fixture["match_id"] for fixture in matches]
        counts = event_annotation_counts(match_ids)
        for fixture in matches:
            fixture["annotation_count"] = counts.get(fixture["match_id"], 0)

        annotations = list_event_annotations(match_ids=match_ids)
        fixture_by_id = {fixture["match_id"]: fixture for fixture in matches}
        for item in annotations:
            item["fixture"] = fixture_by_id.get(item.get("match_id"))
    except PostgresError as exc:
        get_db().rollback()
        annotations = []
        error_message = f"Match filters are unavailable: {exc}"
    except PyMongoError as exc:
        annotations = []
        error_message = f"MongoDB event annotations are unavailable: {exc}"
    except RuntimeError as exc:
        annotations = []
        error_message = str(exc)

    return render_template(
        "admin_event_annotations.html",
        title="MongoDB Event Annotation Studio",
        annotations=annotations,
        matches=matches,
        seasons=seasons,
        teams=teams,
        selected_season=season_name,
        selected_team_id=team_id,
        covered_seasons=covered_seasons,
        error_message=error_message,
    )


@admin_bp.post("/matches/<int:match_id>/event-annotations")
def add_event_annotation_to_match(match_id):
    """Create a MongoDB annotation from a relational match detail page."""
    event_id = request.form.get("event_id", "").strip()
    data, error = annotation_content_form_data()
    if not event_id:
        error = "Choose an actual match event before adding an annotation."
    if error:
        flash(error, "error")
    else:
        try:
            if not match_exists(match_id):
                flash("The selected match does not exist.", "error")
                return redirect(url_for("admin.event_annotations"))
            source_event = get_source_match_event(match_id, event_id)
            if source_event is None:
                flash("That event was not found in this match's MongoDB document.", "error")
                return redirect(
                    url_for("matches.match_detail", match_id=match_id) + "#match-events"
                )
            # CREATE: store a verified snapshot of the selected nested StatsBomb event.
            create_event_annotation(match_id=match_id, event=source_event, **data)
            flash("Event annotation created successfully.", "success")
        except PostgresError as exc:
            get_db().rollback()
            flash(f"Could not validate the match: {exc}", "error")
        except (PyMongoError, RuntimeError) as exc:
            flash(f"Could not create event annotation: {exc}", "error")
    return redirect(url_for("matches.match_detail", match_id=match_id) + "#event-annotations")


@admin_bp.route("/event-annotations/new", methods=["GET", "POST"])
def new_event_annotation():
    flash("Choose a match, then click Annotate beside an actual event.", "success")
    return redirect(url_for("admin.event_annotations"))


@admin_bp.route("/event-annotations/<annotation_id>/edit", methods=["GET", "POST"])
def edit_event_annotation(annotation_id):
    try:
        item = get_event_annotation(annotation_id)
        if item is None:
            flash("Event annotation not found.", "error")
            return redirect(url_for("admin.event_annotations"))

        if request.method == "POST":
            data, error = annotation_content_form_data()
            if error:
                flash(error, "error")
            else:
                # UPDATE: use ObjectId and $set to change the document.
                update_event_annotation(annotation_id, **data)
                flash("Event annotation updated successfully.", "success")
                return_match_id = request.args.get("return_to_match", type=int)
                if return_match_id:
                    return redirect(
                        url_for("matches.match_detail", match_id=return_match_id)
                        + "#event-annotations"
                    )
                return redirect(url_for("admin.event_annotations"))
    except InvalidId:
        flash("Invalid event annotation ID.", "error")
        return redirect(url_for("admin.event_annotations"))
    except (PyMongoError, RuntimeError) as exc:
        flash(f"Could not update event annotation: {exc}", "error")
        return redirect(url_for("admin.event_annotations"))

    return render_template(
        "admin_event_annotation_form.html",
        title="Edit Event Annotation",
        item=item,
        return_match_id=request.args.get("return_to_match", type=int),
    )


@admin_bp.post("/event-annotations/<annotation_id>/delete")
def remove_event_annotation(annotation_id):
    return_match_id = request.form.get("return_to_match", type=int)
    try:
        # DELETE: remove the MongoDB document using its ObjectId.
        if delete_event_annotation(annotation_id):
            flash("Event annotation deleted successfully.", "success")
        else:
            flash("Event annotation not found.", "error")
    except InvalidId:
        flash("Invalid event annotation ID.", "error")
    except (PyMongoError, RuntimeError) as exc:
        flash(f"Could not delete event annotation: {exc}", "error")
    if return_match_id:
        return redirect(
            url_for("matches.match_detail", match_id=return_match_id) + "#event-annotations"
        )
    return redirect(url_for("admin.event_annotations"))
