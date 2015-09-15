from flask import render_template, session, redirect, url_for, request, make_response, abort, flash
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
	page = request.args.get('page', 1, type=int)
	#error_out表示page超过时，True返回404，Flase返回空
	pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
		page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],error_out=True)  
	posts = pagination.items
	return render_template('index.html', posts=posts,pagination=pagination)
	'''
	page = request.args.get('page', 1, type=int)
	show_followed = False
	if current_user.is_authenticated:
		show_followed = bool(request.cookies.get('show_followed', ''))
	if show_followed:
		query = current_user.followed_posts
	else:
		query = Post.query
	pagination = query.order_by(Post.timestamp.desc()).paginate(
			page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
			error_out=False)
	posts = pagination.items
	return render_template('index.html', posts=posts,
				show_followed=show_followed, pagination=pagination)

##设置show_followed的cookies来区别首页显示
@main.route('/all')
@login_required
def show_all():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '', max_age=30*24*60*60)
	return resp

@main.route('/followed')
@login_required
def show_followed():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
	return resp
##^^^^设置show_followed的cookies来区别首页显示

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
	page = request.args.get('page', 1, type=int)
	pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
		page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],error_out=True)
	posts = pagination.items
	return render_template('user.html', user=user, posts=posts, pagination=pagination)


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
		##url_for post前加点是解决一个神奇的bug，大概与Blueprint的工厂模式有关
		return redirect(url_for('.post', id=post.id))
	return render_template('edit.html', post=post)


#关注
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(user):
		flash('You are already following this user.')
		return redirect(url_for('.user', username=username))
	current_user.follow(user)
	flash('You are now following %s.' % username)
	return redirect(url_for('.user', username=username))

#取消关注
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if not current_user.is_following(user):
		flash('You are not following this user.')
		return redirect(url_for('.user', username=username))
	current_user.unfollow(user)
	flash('You are now unfollowing %s.' % username)
	return redirect(url_for('.user', username=username))

#关注我的
@main.route('/followers/<username>')
def followers(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followers.paginate(
			page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
			error_out=False)
	follows = [{'user': item.follower, 'timestamp': item.timestamp}
		for item in pagination.items]
	return render_template('followers.html', user=user, title="Followers of",
						endpoint='.followers', pagination=pagination,
						follows=follows)

#我关注的
@main.route('/followed_by/<username>')
def followed_by(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followed.paginate(
			page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
			error_out=False)
	follows = [{'user': item.followed, 'timestamp': item.timestamp}
		for item in pagination.items]
	return render_template('followers.html', user=user, title="Followed by",
		endpoint='.followed_by', pagination=pagination,
		follows=follows)