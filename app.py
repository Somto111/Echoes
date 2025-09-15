import os
from flask import Flask, render_template, request, url_for, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, login_required, LoginManager, current_user, UserMixin
from sqlalchemy import Select
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'Hello World'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

Allowed_Extensions = {'png','jpg','jpeg', 'gif', 'webp','jfif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in Allowed_Extensions


class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100),unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    author = db.Relationship('Blog', back_populates='post')
    comments = db.Relationship('Comment', back_populates='commenter')
    likes = db.relationship('Like', back_populates='user')

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(200))
    post = db.Relationship('User', back_populates='author')
    comments = db.Relationship('Comment', back_populates='posts')
    likes = db.relationship('Like', back_populates='post')

class Comment(db.Model):
    id = db.Column(db.Integer,  primary_key=True)
    text=db.Column(db.String(300), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    commenter = db.Relationship('User', back_populates='comments')
    posts= db.relationship('Blog', back_populates='comments')


class Like(db.Model):
    id = db.Column(db.Integer,  primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    user = db.relationship('User', back_populates='likes')
    post = db.relationship('Blog', back_populates='likes')




with app.app_context():
    db.create_all()



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/signup', methods=(['GET', 'POST']))
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        new_user = User(name=name, email=email, password=password)
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash('This Email is already in use.', category='error')
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('blog'))
    return render_template("signup.html")


@app.route('/login', methods=(['GET', 'POST']))
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        email_check = db.select(User).where(User.email == email)
        check = db.session.execute(email_check).scalar()

        if check:
            if check.password == password:
                login_user(check)
                return redirect(url_for('blog'))
    return render_template("login.html")


@app.route('/blog')
def blog():
    state = db.select(Blog)
    all_my_post = db.session.execute(state).scalars()
    return render_template("blog.html", post=all_my_post)


@app.route('/create', methods=(['GET', 'POST']))
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image= request.files.get('image')

        image_url = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f"/{image_path}"

        post = Blog(title=title, content=content, user_id=current_user.id, image_url=image_url)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('blog', post_id=post.id))
    return render_template("create.html")


@app.route('/edit/<post_id>', methods=(['GET', 'POST']))
def edit(post_id):
    post = Blog.query.get(post_id)
    particular_post = Select(Blog).where(Blog.id == post_id)
    executed_post = db.session.execute(particular_post).scalar()
    if request.method == 'POST':
        my_title = request.form.get('title')
        my_content = request.form.get('content')
        executed_post.title = my_title
        executed_post.content = my_content
        db.session.commit()
        return redirect(url_for('blog'))
    return render_template("edit.html", post=post)


@app.route('/delete/<post_id>', methods=(['GET', 'POST']))
def delete(post_id):
    particular_post = Select(Blog).where(Blog.id == post_id)
    executed_post = db.session.execute(particular_post).scalar()
    db.session.delete(executed_post)
    db.session.commit()
    return redirect(url_for('blog'))


@app.route('/comments/<int:post_id>', methods=(['GET', 'POST']))
@login_required
def comments(post_id):
    text = request.form.get('text')

    if not text:
        flash('Comment cannot be empty.', category='error')
    else:
        post = Blog.query.filter_by(id=post_id).first()
        if post:
            comment = Comment(text=text, user_id=current_user.id, post=post_id)
            db.session.add(comment)
            db.session.commit()
        else:
            flash('Post does not exist.', category='error')
    return redirect(url_for('blog'))


@app.route('/reviews')
def reviews():
    return render_template("reviews.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signup'))

@app.route('/readmore/<post_id>')
def readmore(post_id):
    particular_post = Select(Blog).where(Blog.id== post_id)
    executed_post=db.session.execute(particular_post).scalar()
    return render_template("readmore.html")


@app.route('/admin')
# @login_required
def admin():
    id =current_user.id
    if id ==1:
        users = User.query.all()
        return render_template("admin.html", users=users)
    else:
        flash("Sorry you must be the admin to access that page")
        return redirect(url_for('login'))


@app.route('/like/<int:post_id>', methods=(['GET']))
@login_required
def likes(post_id):
    post= Blog.query.filter_by(id=post_id).first()
    like= Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if not post:
        flash('Post does not exist', category='error')
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        db.session.commit()
    return redirect(url_for('blog'))


if __name__ == '__main__':
    app.run(debug=True)
