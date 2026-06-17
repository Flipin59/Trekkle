from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
@app.route("/")
def home():
    return render_template("index.html",loggedIn=False)

if __name__=="__main__":
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True)