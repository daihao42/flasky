from flask import render_template, session, redirect, url_for, request
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