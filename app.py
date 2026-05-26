# import the Flask library
from flask import Flask, render_template
from Backend.db_conn import get_db, init_app

# Create the Flask instance and pass the Flask
# constructor, the path of the correct module
app = Flask(__name__, template_folder="Frontend")
init_app(app)

# Default route added using a decorator, for view function 'welcome'
# We pass a simple string to the frontend browser
@app.route('/')
def home():

    return render_template("index.html", title="Home")

@app.route('/db')
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM player;")
    version = cur.fetchall()
    cur.close()
    return str(version)

# Start with flask web app, with debug as True,# only if this is the starting page
if(__name__ == "__main__"):
    app.run(debug=True)