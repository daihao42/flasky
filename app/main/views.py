from flask import render_template, session, redirect, url_for, request, make_response, abort
from . import main
from .. import db
from ..models import User, Permission
from flask.ext.login import login_required
from app.decorators import admin_required, permission_required

@main.route('/', methods=['GET', 'POST'])
def index():
	return render_template('index.html')

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
	if request.method == 'POST':
		if request.form['username'] != current_user.username and \
			User.query.filter_by(username=request.form['username']).first():
			return make_response('username has used', 500)
		current_user.username = request.form['username']
		current_user.location = request.form['location']
		current_user.about_me = request.form['about_me']
		db.session.add(current_user)
	return render_template('user.html', user=user)

'''
#edit personal center
from flask.ext.login import current_user
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	if request.method == 'POST':
		if request.form['username'] != current_user.username and \
			User.query.filter_by(username=request.form['username']).first():
			return make_response('username has used', 500)
		current_user.username = request.form['username']
		current_user.location = request.form['location']
		current_user.about_me = request.form['about_me']
		db.session.add(current_user)
	return render_template('user.html', user=user)
'''

'''
#admin edit one's personal info by id
@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
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
		db.session.add(current_user)
	return render_template('user.html', user=user)
	'''