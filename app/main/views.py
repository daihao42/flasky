from flask import render_template, session, redirect, url_for, request, make_response, abort
from . import main
from .. import db
from ..models import User, Permission, Post
from flask.ext.login import login_required
from app.decorators import admin_required, permission_required
from flask.ext.login import current_user
from flask import current_app

@main.route('/', methods=['GET', 'POST'])
def index():
	'''
	if request.method == 'POST':
		post = Post(title=request.form['title'],
			body=request.form['body'],
			author=current_user._get_current_object())
		db.session.add(post)
		'''
	page = request.args.get('page', 1, type=int)
	#error_out表示page超过时，True返回404，Flase返回空
	pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
		page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],error_out=True)  
	posts = pagination.items
	return render_template('index.html', posts=posts,pagination=pagination)


#test adminstrator
@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
	return "For administrators!"

#test moderate
@main.route('/moderator')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def for_moderators_only():
	return "For comment moderators!"

#personal center
@main.route('/user/<username>')
def user(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		abort(404)
	posts = user.posts.order_by(Post.timestamp.desc()).all()
	return render_template('user.html', user=user, posts=posts)


#edit personal center
@main.route('/edit-profile/<username>', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
	user = User.query.filter_by(username=username).first()
	if user != current_user:
		abort(403)
	if request.method == 'POST':
		if request.form['username'] != current_user.username and \
			User.query.filter_by(username=request.form['username']).first():
			return make_response('username has used', 500)
		current_user.username = request.form['username']
		current_user.location = request.form['location']
		current_user.about_me = request.form['about_me']
		db.session.add(current_user)
	return render_template('edit_profile.html', user=user)



#admin edit one's personal info by id
@main.route('/admin_edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
	user = User.query.get_or_404(id)
	if request.method == 'POST':
		if request.form['username'] != user.username and \
			User.query.filter_by(username=request.form['username']).first():
			return make_response('username has used', 500)
		user.username = request.form['username']
		user.location = request.form['location']
		user.about_me = request.form['about_me']
		db.session.add(user)
	return render_template('edit_profile.html', user=user)


##edit new blog 
@main.route('/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.WRITE_ARTICLES)
def edit_blog():
	if current_user.can(Permission.WRITE_ARTICLES) and \
							request.method == 'POST':
		post = Post(title=request.form['title'],
			body=request.form['body'],
			author=current_user._get_current_object())
		db.session.add(post)
		return redirect('/')
	return render_template('edit.html')

#single blog
@main.route('/post/<int:id>')
def post(id):
	post = Post.query.get_or_404(id)
	return render_template('post.html', post=post)

#edit blog which is alive
@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id)
	if current_user != post.author and \
			not current_user.can(Permission.ADMINISTER):
		abort(403)
	if request.method == 'POST':
		post.title = request.form['title']
		post.body = request.form['body']
		db.session.add(post)
		return redirect(url_for('.post', id=post.id))
	return render_template('edit.html', post=post)