from flask import render_template, session, redirect, url_for, request, make_response, abort, flash
from . import main
from .. import db
from ..models import User, Permission, Post, Comment
from flask.ext.login import login_required
from app.decorators import admin_required, permission_required
from flask.ext.login import current_user
from flask import current_app
import os
from werkzeug import secure_filename

@main.route('/', methods=['GET', 'POST'])
def index():
	page = request.args.get('page', 1, type=int)
	show_followed = False
	if current_user.is_authenticated:
		show_followed = bool(request.cookies.get('show_followed', ''))
	if show_followed:
		query = current_user.followed_posts
	else:
		query = Post.query
	#error_out表示page超过时，True返回404，Flase返回空
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
		user.role_id = request.form['role_id']
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
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
	post = Post.query.get_or_404(id)
	if request.method == 'POST':
		comment = Comment(body=request.form['body'],
					post=post,
					author=current_user._get_current_object())
		db.session.add(comment)
		flash('Your comment has been published.')
		'''
		return redirect(url_for('.post', id=post.id, page=-1))
	page = request.args.get('page', 1, type=int)
	if page == -1:
		page = (post.comments.count() - 1) / \
			current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
			'''
		return redirect(url_for('.post', id=post.id))
	page = request.args.get('page', 1, type=int)

	pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
				page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
				error_out=False)
	comments = pagination.items
	return render_template('post.html', post=post, 
							comments=comments, pagination=pagination)

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

#delete blog
@main.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
	post = Post.query.get_or_404(id)
	if current_user != post.author and \
			not current_user.can(Permission.ADMINISTER):
		abort(403)
	for comment in post.comments:
		db.session.delete(comment)
	username = post.author.username
	title = post.title
	db.session.delete(post)
	flash('你的Blog %s 被删除了!' % title)
	return redirect(url_for('.user', username = username))



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
	flash('你现在关注了 %s.' % username)
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
	flash('你现在取关了 %s.' % username)
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

#协管员管理评论页面
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
	page = request.args.get('page', 1, type=int)
	pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
			page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
			error_out=False)
	comments = pagination.items
	return render_template('moderate.html', comments=comments,
							pagination=pagination, page=page)

#协管员允许评论
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = False
	db.session.add(comment)
	return redirect(url_for('.moderate',
			page=request.args.get('page', 1, type=int)))

#协管员禁止评论
@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = True
	db.session.add(comment)
	return redirect(url_for('.moderate',
			page=request.args.get('page', 1, type=int)))


##上传头像
@main.route('/uploadimg/<int:id>',methods=['GET', 'POST'])
@login_required
def uploadimg(id):
	if request.method == 'POST':
		f = request.files['file']
		path=os.path.abspath('.')
		path=os.path.join(path,"app")
		path=os.path.join(path,"static")
		path=os.path.join(path,"headimg")
		suffix=os.path.splitext(secure_filename(f.filename))[1][1:]
		path=os.path.join(path,"%s.%s" % (id,suffix))
		f.save(path)
		user = User.query.get_or_404(id)
		user.image = '/static/headimg/%s.%s' % (id,suffix)
		db.session.add(user) 
	return 'upload ok'
