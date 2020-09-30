"""Insta485 model (database) API."""
import sqlite3
import flask
import insta485
import uuid
import hashlib
import pathlib
import os
import arrow

def dict_factory(cursor, row):
    """Convert database row objects to a dictionary keyed on column name.

    This is useful for building dictionaries which are then used to render a
    template.  Note that this would be inefficient for large queries.
    """
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_db():
    """Open a new database connection.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    if 'sqlite_db' not in flask.g:
        db_filename = insta485.app.config['DATABASE_FILENAME']
        flask.g.sqlite_db = sqlite3.connect(str(db_filename))
        flask.g.sqlite_db.row_factory = dict_factory

        # Foreign keys have to be enabled per-connection.  This is an sqlite3
        # backwards compatibility thing.
        flask.g.sqlite_db.execute("PRAGMA foreign_keys = ON")

    return flask.g.sqlite_db


@insta485.app.teardown_appcontext
def close_db(error):
    """Close the database at the end of a request.

    Flask docs:
    https://flask.palletsprojects.com/en/1.0.x/appcontext/#storing-data
    """
    assert error or not error  # Needed to avoid superfluous style error
    sqlite_db = flask.g.pop('sqlite_db', None)
    if sqlite_db is not None:
        sqlite_db.commit()
        sqlite_db.close()

def createPost():
    connection = insta485.model.get_db()
    # Unpack flask object
    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    # Compute base name (filename without directory).  We use a UUID to avoid
    # clashes with existing files, and ensure that the name is compatible with the
    # filesystem.
    uuid_basename = "{stem}{suffix}".format(
        stem=uuid.uuid4().hex,
        suffix=pathlib.Path(filename).suffix
    )

    # Save to disk
    path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
    params = (str(uuid_basename), str(flask.session["username"]))
    try:
        cur = connection.execute("INSERT INTO posts ( filename, owner ) VALUES (?, ?)", params)
        fileobj.save(path)

    except sqlite3.Error as e:
        flask.abort(409)


    return showUser(flask.session["username"])


def login(username, password):
    params = (username, 1)
    try:
        connection = insta485.model.get_db()
        cur = connection.execute("SELECT * FROM users WHERE username LIKE ? AND 1 = ?", params)
        users = cur.fetchall()
        if (len(users) == 0):
            flask.abort(403)
        password = str(users[0]['password'])
        splitpassword = password.split('$')
        salt = splitpassword[1]
        algorithm = 'sha512'
        hash_obj = hashlib.new(algorithm)
        password_salted = salt + password
        hash_obj.update(password_salted.encode('utf-8'))
        password_hash = hash_obj.hexdigest()
        password_db_string = "$".join([algorithm, salt, password_hash])
        flask.session.clear()
        flask.session["username"] = str(users[0]['username'])
        flask.session["fullname"] = str(users[0]['fullname'])
        flask.session["email"] = str(users[0]['email'])
        flask.session["filename"] = str(users[0]['filename'])
    except sqlite3.Error as e:
        flask.abort(402)



def create(file, fullname, username, email, password):
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + password
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])
    connection = insta485.model.get_db()
    # Unpack flask object
    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    # Compute base name (filename without directory).  We use a UUID to avoid
    # clashes with existing files, and ensure that the name is compatible with the
    # filesystem.
    uuid_basename = "{stem}{suffix}".format(
        stem=uuid.uuid4().hex,
        suffix=pathlib.Path(filename).suffix
    )

    # Save to disk
    path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
    params = (str(username), str(password_db_string), str(uuid_basename), str(fullname), str(email))
    try:
        cur = connection.execute("INSERT INTO users (username, password, filename, fullname, email ) VALUES (?, ?, ?, ?, ?)", params)

        fileobj.save(path)
        flask.session.clear()
        flask.session["username"] = str(username)
        flask.session["fullname"] = str(fullname)
        flask.session["email"] = str(email)
        flask.session["filename"] = str(uuid_basename)
    except sqlite3.Error as e:
        flask.abort(409)

    return flask.redirect(flask.url_for("show_index"))



def edit(fullname, email):
    if flask.request.files['file'].filename != '':
        filename = flask.session["filename"]

        # Save to disk
        path = insta485.app.config["UPLOAD_FOLDER"]/filename
        os.remove(path)

        ############## Upload Image
        fileobj = flask.request.files["file"]
        filename2 = fileobj.filename

        # Compute base name (filename without directory).  We use a UUID to avoid
        # clashes with existing files, and ensure that the name is compatible with the
        # filesystem.
        uuid_basename = "{stem}{suffix}".format(
            stem=uuid.uuid4().hex,
            suffix=pathlib.Path(filename2).suffix
        )

        # Save to disk
        path2 = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
        fileobj.save(path2)
        flask.session["filename"] = filename2
        connection = insta485.model.get_db()
        params = (fullname, email, uuid_basename, flask.session["username"])
        try:
            cur = connection.execute("UPDATE users SET fullname = ?, email = ?, filename = ? WHERE username = ?", params)
            flask.session["fullname"] = fullname
            flask.session["email"] = email
        except Exception as e:
            raise
    else:
        connection = insta485.model.get_db()
        params = (fullname, email, flask.session["username"])
        try:
            cur = connection.execute("UPDATE users SET fullname = ?, email = ? WHERE username = ?", params)
            flask.session["fullname"] = fullname
            flask.session["email"] = email
        except Exception as e:
            raise

def delete():
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), 1)
    query = "DELETE FROM users WHERE username = ? AND 1 = ?"
    cur = connection.execute(query,params)
    filename = flask.session["filename"]
    path = insta485.app.config["UPLOAD_FOLDER"]/filename
    os.remove(path)
    flask.session.clear()


def password(password, new_password1, new_password2):
    connection = insta485.model.get_db()
    if new_password1 != new_password2:
        flask.abort(401)
    params = [str(session[username])]
    cur = connection.execute("SELECT * FROM users WHERE username LIKE ?", params)
    users = cur.fetchall()
    if len(users) > 0 and (str(users[0]['password'] == str(password_db_string))):
        params = [new_password1, flask.session["username"]]
        cur = connection.execute("UPDATE users SET password = ? WHERE username = ?", params)
        return flask.redirect(flask.url_for("edit"))


def setIndex():
    connection = insta485.model.get_db()

    # Query database
    cur = connection.execute(
        "SELECT * "
        "FROM posts ORDER BY postid DESC"
    )
    posts = cur.fetchall()
    cur1 = connection.execute(
        "SELECT * "
        "FROM comments"
    )
    comments = cur1.fetchall()

    cur2 = connection.execute(
        "SELECT * "
        "FROM likes"
    )
    likes = cur2.fetchall()

    cur3 = connection.execute(
        "SELECT * "
        "FROM users"
    )
    users = cur3.fetchall()
    for post in posts:
        post['filename'] = "/uploads/" + post['filename']
        post['numberOfLikes'] = 0
        post['likes'] = []
        post['comments'] = []
        post['created'] = arrow.get(post['created']).humanize()
        post['iLike'] = 0
        for like in likes:
            if like['postid'] == post['postid']:
                post['numberOfLikes'] += 1
                post['likes'].append(like)
                if like['owner'] == flask.session['username']:
                    post['iLike'] = 1
        for comment in comments:
            if comment['postid'] == post['postid']:
                post['comments'].append(comment)
        for user in users:
            if user['username'] == post['owner']:
                post['owner_img_url'] = user['filename']

    # Add database info to context
    context = {"posts": posts, "username" : flask.session["username"]}
    return flask.render_template("index.html", **context)


def likePost(postid):
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), int(postid))
    try:
        cur = connection.execute("INSERT INTO likes (owner, postid ) VALUES (?, ?)", params)
    except Exception as e:
        raise
    return

def unlikePost(postid):
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), postid)
    try:
        cur = connection.execute("DELETE FROM likes where owner = ? AND postid = ?", params)
    except Exception as e:
        raise
    return

def addComment(postid, text):
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), postid, text)
    try:
        cur = connection.execute("INSERT INTO comments (owner, postid, text ) VALUES (?, ?, ?)", params)
    except Exception as e:
        raise
    return setIndex()

def deleteComment(id):
    connection = insta485.model.get_db()
    params = (id, str(flask.session["username"]))
    try:
        cur = connection.execute("DELETE FROM comments where commentid = ? AND owner = ?", params)
    except Exception as e:
        flask.abort(403)
        raise
    return setIndex()

def deletePost(id):
    connection = insta485.model.get_db()
    params = (id, str(flask.session["username"]))
    try:
        cur = connection.execute("DELETE FROM posts where postid = ? AND owner = ?", params)
    except Exception as e:
        flask.abort(403)
        raise
    return


def followUser(username):
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), str(username))
    try:
        cur = connection.execute("INSERT INTO following (username1, username2 ) VALUES (?, ?)", params)
    except Exception as e:
        raise
    return showUser(username)

def unfollowUser(username):
    connection = insta485.model.get_db()
    params = (str(flask.session["username"]), str(username))
    try:
        cur = connection.execute("DELETE FROM following where username1 = ? AND username2 = ?", params)
    except Exception as e:
        raise
    return showUser(username)

def showUser(username_url_slug):
    connection = insta485.model.get_db()


    cur = connection.execute(
        "SELECT * "
        "FROM users"
    )
    users = cur.fetchall()
    for user in users:
        if user['username'] == username_url_slug:
            cur2 = connection.execute(
                "SELECT * "
                "FROM posts"
            )
            posts = cur2.fetchall()
            userposts = []
            total_posts = 0
            for post in posts:
                if post["owner"] == username_url_slug:
                    userposts.append(post)
                    total_posts += 1


            cur3 = connection.execute(
                "SELECT * "
                "FROM following"
            )
            followers = cur3.fetchall()
            followersCount = 0
            followingCount = 0
            isFollowing = 0
            context = {"user": user}
            for follower in followers:
                if follower['username1'] == flask.session["username"] and follower['username2'] == username_url_slug:
                    isFollowing = 1
                if follower['username2'] == username_url_slug:
                    followersCount += 1
                if follower['username1'] == username_url_slug:
                    followingCount += 1
            if username_url_slug == flask.session["username"]:
                context = {"user": user, "username" : flask.session["username"], "isFollowing": 0, "total_posts": total_posts, "posts": userposts,"followers": followersCount,"following": followingCount}
                return flask.render_template("user.html", **context)
            context = {"user": user, "username" : flask.session["username"], "isFollowing": isFollowing, "total_posts": total_posts, "posts": userposts,"followers": followersCount,"following": followingCount}

            return flask.render_template("user.html", **context)
    return flask.redirect(flask.url_for("show_index"))

def showFollowers(username_url_slug):
    connection = insta485.model.get_db()

    cur = connection.execute(
        "SELECT * "
        "FROM following"
    )
    follows = cur.fetchall()
    userfollows = []
    cur1 = connection.execute(
        "SELECT * "
        "FROM users"
    )
    users = cur1.fetchall()
    good = 0
    for user in users:
        if user['username'] == username_url_slug:
            good = 1
    if good == 0:
        return flask.redirect(flask.url_for("show_index"))
    for follow in follows:
        follow['logname_follows_username'] = 0
        name = follow['username1']
        if follow['username2'] == username_url_slug:
            for follow1 in follows:
                if flask.session["username"] == follow1['username1'] and follow1['username2'] == follow['username1']:
                    follow['logname_follows_username'] = 1
            for user in users:
                if user['username'] == follow['username1']:
                    follow['user_img_url'] = "/uploads/" + user['filename']
            userfollows.append(follow)
    context = {"followers": userfollows, "username" : flask.session["username"]}
    return flask.render_template("followers.html", **context)


def showFollowing(username_url_slug):
    connection = insta485.model.get_db()

    cur = connection.execute(
        "SELECT * "
        "FROM following"
    )
    follows = cur.fetchall()
    userfollows = []
    cur1 = connection.execute(
        "SELECT * "
        "FROM users"
    )
    users = cur1.fetchall()
    good = 0
    for user in users:
        if user['username'] == username_url_slug:
            good = 1
    if good == 0:
        return flask.redirect(flask.url_for("show_index"))
    for follow in follows:
        follow['logname_follows_username'] = 0
        name = follow['username2']
        if follow['username1'] == username_url_slug:
            userfollows.append(follow)
            for follow1 in follows:
                if flask.session["username"] == follow1['username2'] and follow1['username1'] == follow['username2']:
                    follow['logname_follows_username'] = 1
            for user in users:
                if user['username'] == follow['username2']:
                    follow['user_img_url'] = "/uploads/" + user['filename']
    context = {"followers": userfollows, "username" : flask.session["username"]}
    return flask.render_template("following.html", **context)


def showPost(postid_url_slug):
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * "
        "FROM posts"
    )
    posts = cur.fetchall()

    for post in posts:

        if str(post['postid']) == postid_url_slug:

            cur1 = connection.execute(
                "SELECT * "
                "FROM users"
            )
            users = cur1.fetchall()
            for user in users:
                if user['username'] == post['owner']:
                    post['owner_img_url'] = "/uploads/" + user['filename']
                    post['img_url'] = "/uploads/" + post['filename']
                    post['iLike'] = 0
                    post['likes'] = 0
                    cur2 = connection.execute(
                        "SELECT * "
                        "FROM likes"
                    )
                    likes = cur2.fetchall()
                    for like in likes:
                        if like['postid'] == post['postid']:
                            post['likes'] += 1
                            if like['owner'] == flask.session["username"]:
                                post['iLike'] = 1
                    cur3 = connection.execute(
                        "SELECT * "
                        "FROM comments"
                    )
                    comments = cur3.fetchall()
                    post_comments = []
                    for comment in comments:
                        if comment['postid'] == post['postid']:
                            post_comments.append(comment)
                    post['comments'] = post_comments
                    post['created'] = arrow.get(post['created']).humanize()
                    context = {"post": post, "username" : flask.session["username"]}
                    return flask.render_template("post.html", **context)
    return flask.redirect(flask.url_for("login"))

def explore():
    connection = insta485.model.get_db()

    dontinclude = []

    cur1 = connection.execute(
        "SELECT * "
        "FROM following"
    )
    follows = cur1.fetchall()
    for follow in follows:
        if str(flask.session["username"]) == follow['username1']:
            dontinclude.append(follow['username2'])
    doinclude = []
    cur = connection.execute(
        "SELECT * "
        "FROM users"
    )
    users = cur.fetchall()
    for user in users:
        if user['username'] not in dontinclude and user['username'] != str(flask.session["username"]):
            user['user_img_url'] = "/uploads/" + user['filename']
            doinclude.append(user)
    context = {"users": doinclude, "username" : flask.session["username"]}
    return flask.render_template("explore.html", **context)
