from flask import render_template, redirect, request, url_for, make_response, flash
from flask.ext.login import login_user
from flask.ext.login import logout_user, login_required
from ..models import User
from . import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		user = User.query.filter_by(email=request.form['email']).first()
		if user is None:
			return make_response('Invalid e-mail', 500)
		elif not user.verify_password(request.form.get('passwd')):
			return make_response('Invalid password', 500)
		else:
			login_user(user, True)
	return render_template('auth/login.html')


#logout
@auth.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect('/')