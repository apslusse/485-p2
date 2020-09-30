"""
Insta485 index (main) view.

URLs include:
/
"""
import flask
import insta485
import os

@insta485.app.route('/', methods=['GET', 'POST'])
def show_index():
    """Display / route."""
    if flask.request.method == 'POST':
        postid = int(flask.request.values.get('postid'))
        text = flask.request.values.get('text')
        submit = flask.request.values.get('which')

        if str(submit) == 'like':
            insta485.model.likePost(postid)
        elif str(submit) == 'unlike':
            insta485.model.unlikePost(postid)
        else:
            return insta485.model.addComment(postid, text)
    if "username" in flask.session:
        # Connect to database
        return insta485.model.setIndex()
    else:
        return flask.render_template("login.html")



@insta485.app.route('/accounts/login/', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST':
        username = str(flask.request.values.get('username'))
        password = str(flask.request.values.get('password'))
        return insta485.model.login(username, password)
    else:
        if "username" in flask.session:
            return flask.redirect(flask.url_for("show_index"))
        return flask.render_template("login.html")


@insta485.app.route('/accounts/create/', methods=['GET', 'POST'])
def create():
    if flask.request.method == 'POST':
        username = flask.request.values.get('username')
        password = flask.request.values.get('password')
        file = flask.request.values.get('file')
        fullname = flask.request.values.get('fullname')
        email = flask.request.values.get('email')
        if str(password) == "":
            flask.abort(400)
        return insta485.model.create( file, fullname, username, email, password)
    else:
        return flask.render_template("create.html")

@insta485.app.route('/accounts/logout/', methods=['POST'])
def logout():
    flask.session.clear()
    return flask.redirect(flask.url_for("login"))

@insta485.app.route('/accounts/edit/', methods=['GET','POST'])
def edit():
    if "username" in flask.session:
        if flask.request.method == 'POST':
            insta485.model.edit(flask.request.values.get('fullname'), flask.request.values.get('email'))
            context = {"username" : flask.session["username"], "filename" : flask.session["filename"], "fullname" : flask.session["fullname"], "email" : flask.session["email"] }
            return flask.render_template("edit.html", **context)
        else:
            context = {"username" : flask.session["username"], "filename" : flask.session["filename"], "fullname" : flask.session["fullname"], "email" : flask.session["email"] }
            return flask.render_template("edit.html", **context)
    else:
        return flask.redirect(flask.url_for("login"))

@insta485.app.route('/accounts/delete/', methods=['GET', 'POST'])
def delete():
    if "username" in flask.session:
        if flask.request.method == 'POST':
            insta485.model.delete()
            flask.session.clear()
            return flask.redirect(flask.url_for("create"))
        else:
            context = {"username" : flask.session["username"] }
            return flask.render_template("delete.html", **context)
    flask.abort(403)



@insta485.app.route('/accounts/password/', methods=['GET', 'POST'])
def password():
    if "username" in flask.session:
        if flask.request.method == 'POST':
            return insta485.model.password(password, new_password1, new_password2)
        else:
            context = {"username" : flask.session["username"] }
            return flask.render_template("password.html", **context)
    else:
        return flask.redirect(flask.url_for("login"))

@insta485.app.route("/u/<username_url_slug>/", methods=["GET", "POST"])
def user(username_url_slug):
    if flask.request.method == 'POST':
        submit = flask.request.values.get('which')
        if str(submit) == 'follow':
            return insta485.model.followUser(username_url_slug)
        elif str(submit) == 'unfollow':
            return insta485.model.unfollowUser(username_url_slug)
        elif str(submit) == 'create_post':
            return insta485.model.createPost()

    return insta485.model.showUser(username_url_slug)

@insta485.app.route("/u/<username_url_slug>/followers/", methods=["GET", "POST"])
def followers(username_url_slug):
    if flask.request.method == 'POST':
        submit = flask.request.values.get('which')
        if str(submit) == 'follow':
            return insta485.model.followUser(username_url_slug)
        elif str(submit) == 'unfollow':
            return insta485.model.unfollowUser(username_url_slug)

    return insta485.model.showFollowers(username_url_slug)

@insta485.app.route("/u/<username_url_slug>/following/", methods=["GET", "POST"])
def following(username_url_slug):
    if flask.request.method == 'POST':
        submit = flask.request.values.get('which')
        if str(submit) == 'follow':
            return insta485.model.followUser(username_url_slug)
        elif str(submit) == 'unfollow':
            return insta485.model.unfollowUser(username_url_slug)

    return insta485.model.showFollowing(username_url_slug)

@insta485.app.route("/p/<postid_url_slug>/", methods=["GET", "POST"])
def post(postid_url_slug):
    if flask.request.method == 'POST':
        submit = flask.request.values.get('which')
        if str(submit) == 'like':
            insta485.model.likePost(postid_url_slug)
        elif str(submit) == 'unlike':
            insta485.model.unlikePost(postid_url_slug)
        elif str(submit) == 'comment':
            text = flask.request.values.get('text')
            return insta485.model.comment(postid_url_slug, text)
        elif str(submit) == 'deletecomment':
            id = flask.request.values.get('commentid')
            return insta485.model.deleteComment(id)
        elif str(submit) == 'deletepost':
            return insta485.model.deletePost(postid_url_slug)

    return insta485.model.showPost(postid_url_slug)

@insta485.app.route("/explore/", methods=["GET", "POST"])
def explore():
    if flask.request.method == 'POST':
        submit = flask.request.values.get('which')
        username = flask.request.values.get('username')
        if str(submit) == 'follow':
            return insta485.model.followUser(username)
    return insta485.model.explore()
