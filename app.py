from enum import unique

from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
bcrypt = Bcrypt()
migrate = Migrate(app, db)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    comments = db.relationship('Comment', back_populates='user')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', back_populates='article')
    user = db.relationship('User', backref='articles')

    def __repr__(self):
        return '<Article %r' % self.id


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    user = db.relationship('User', back_populates='comments')
    article = db.relationship('Article', back_populates='comments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@app.route('/home')
def index():
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Такой пользователь уже существует!", "danger")
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Вы успешно зарегистрировались!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Вы успешно вошли!", "success")
            return redirect(url_for('index'))
        else:
            flash("Неверное имя пользователя или пароль!", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/posts')
def posts():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template("posts.html", articles=articles)


@app.route('/posts/<int:id>')
def post_detail(id):
    article = Article.query.get(id)
    return render_template("post_detail.html", article=article)


@app.route('/posts/<int:id>/delete')
def post_delete(id):
    article = Article.query.get_or_404(id)

    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/posts')
    except:
        return "При удалении статьи произошла ошибка"


@app.route('/posts/<int:id>/update', methods=['POST', 'GET'])
def post_update(id):
    article = Article.query.get(id)

    if request.method == "POST":
        article.title = request.form['title']
        article.intro = request.form['intro']
        article.text = request.form['text']

        try:
            db.session.commit()
            return redirect('/posts')
        except:
            return "При редактировании статьи произошла ошибка"

    else:
        return render_template("post_update.html", article=article)


@app.route('/posts/<int:article_id>/comment', methods=['POST'])
@login_required
def add_comment(article_id):
    text = request.form['text']
    comment = Comment(text=text, user_id=current_user.id, article_id=article_id)

    try:
        db.session.add(comment)
        db.session.commit()
        return redirect(f'/posts/{article_id}')
    except:
        return "При добавлении комментария произошла ошибка"


@app.route('/posts/<int:article_id>/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(article_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    article = Article.query.get(article_id)

    if request.method == 'POST':
        comment.text = request.form['text']
        try:
            db.session.commit()
            return redirect(f'/posts/{article_id}')
        except:
            return "При редактировании комментария произошла ошибка!"

    return render_template('edit_comment.html', comment=comment, article=article)


@app.route('/posts/<int:article_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(article_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)

    try:
        db.session.delete(comment)
        db.session.commit()
        return redirect(f'/posts/{article_id}')
    except:
        return "При удалении комментария произошла ошибка"


@app.route('/create-article', methods=['POST', 'GET'])
@login_required
def create_article():
    if request.method == "POST":
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']

        article = Article(title=title, intro=intro, text=text, user_id=current_user.id)

        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/posts')
        except:
            return "При добавлении статьи произошла ошибка"
    else:
        return render_template("create-article.html")


if __name__ == "__main__":
    app.run(debug=True)