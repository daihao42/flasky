import datetime
from app import db
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin, AnonymousUserMixin

from markdown import markdown
import bleach

##权限配置
class Permission:
	FOLLOW = 0x01
	COMMENT = 0x02
	WRITE_ARTICLES = 0x04
	MODERATE_COMMENTS = 0x08
	ADMINISTER = 0x80
	

#关注关系表
class Follow(db.Model):
	__tablename__ = 'follows'
	follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
							primary_key=True)
	followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
							primary_key=True)
	timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


#角色
class Role(db.Model):
	__tablename__ = 'roles'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	default = db.Column(db.Boolean, default=False, index=True)
	permissions = db.Column(db.Integer)
	users = db.relationship('User', backref='role', lazy='dynamic')

	#角色权限分配
	@staticmethod
	def insert_roles():
		roles = {
			'User': (Permission.FOLLOW |
					 Permission.COMMENT |
					 Permission.WRITE_ARTICLES, True),
			'Moderator': (Permission.FOLLOW |
						  Permission.COMMENT |
						  Permission.WRITE_ARTICLES |
						  Permission.MODERATE_COMMENTS, False),
			'Administrator': (0xff, False)
		}
		for r in roles:
			role = Role.query.filter_by(name=r).first()
			if role is None:
				role = Role(name=r)
			role.permissions = roles[r][0]
			role.default = roles[r][1]
			db.session.add(role)
		db.session.commit()
	def __repr__(self):
		return '<Role %r>' % self.name


class User(UserMixin,db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(64), unique=True, index=True)
	username = db.Column(db.String(64), unique=True, index=True)
	password_hash = db.Column(db.String(128))
	image = db.Column(db.String(64))
	role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
	location = db.Column(db.String(64))
	about_me = db.Column(db.Text())
	member_since = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
	last_seen = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
	posts = db.relationship('Post', backref='author', lazy='dynamic')
	comments = db.relationship('Comment', backref='author', lazy='dynamic')

	##关注外键关系表
	followed = db.relationship('Follow',
					foreign_keys=[Follow.follower_id],
					backref=db.backref('follower', lazy='joined'),
					lazy='dynamic',
					cascade='all, delete-orphan')
	followers = db.relationship('Follow',
					foreign_keys=[Follow.followed_id],
					backref=db.backref('followed', lazy='joined'),
					lazy='dynamic',
					cascade='all, delete-orphan')

	def __init__(self, **kwargs):
		super(User, self).__init__(**kwargs)
		if self.role is None:
			if self.email == current_app.config['FLASKY_ADMIN']:
				self.role = Role.query.filter_by(permissions=0xff).first()
			if self.role is None:
				self.role = Role.query.filter_by(default=True).first()

	@property
	def password(self):
		raise AttributeError('password is not a readable attribute')

	@password.setter
	def password(self, password):
		self.password_hash = generate_password_hash(password)

	def verify_password(self, password):
		return check_password_hash(self.password_hash, password)

		#检查用户是否有指定的权限
	def can(self, permissions):
		return self.role is not None and \
			(self.role.permissions & permissions) == permissions

		#检查管理员权限
	def is_administrator(self):
		return self.can(Permission.ADMINISTER)

	#记录最后访问时间
	def ping(self):
		self.last_seen = datetime.datetime.utcnow()
		db.session.add(self)

	#执行关注
	def follow(self, user):
		if not self.is_following(user):
			f = Follow(follower=self, followed=user)
			db.session.add(f)
	#取消关注
	def unfollow(self, user):
		f = self.followed.filter_by(followed_id=user.id).first()
		if f:
			db.session.delete(f)
	#是否关注
	def is_following(self, user):
		return self.followed.filter_by(
				followed_id=user.id).first() is not None
	#是否被关注
	def is_followed_by(self, user):
		return self.followers.filter_by(
				follower_id=user.id).first() is not None

	#我关注的人的blog
	@property
	def followed_posts(self):
		return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
				.filter(Follow.follower_id == self.id)

	#将自己添加为自己关注人以方便在关注的blog中看到自己的blog
	@staticmethod
	def add_self_follows():
		for user in User.query.all():
			if not user.is_following(user):
				user.follow(user)
				db.session.add(user)
				db.session.commit()

	#生成虚拟User测试数据
	@staticmethod
	def generate_fake(count=100):
		from sqlalchemy.exc import IntegrityError
		from random import seed
		import forgery_py

		seed()
		for i in range(count):
			u = User(email=forgery_py.internet.email_address(),
				username=forgery_py.internet.user_name(True),
				password=forgery_py.lorem_ipsum.word(),
				location=forgery_py.address.city(),
				about_me=forgery_py.lorem_ipsum.sentence(),
				member_since=forgery_py.date.date(True))
			db.session.add(u)
			try:
				db.session.commit()
			except IntegrityError:
				db.session.rollback()
	#^^^生成虚拟User测试数据

class AnonymousUser(AnonymousUserMixin):
	def can(self, permissions):
		return False

	def is_administrator(self):
		return False

'''
	flask-login callback func
	使用指定的标识符加载用户
'''
from . import login_manager
@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))

'''
	为未登陆访客分配匿名身份
'''
login_manager.anonymous_user = AnonymousUser


'''
	blog内容
	'''
class Post(db.Model):
	__tablename__ = 'posts'
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(64))
	body = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
	author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	body_html = db.Column(db.Text)
	comments = db.relationship('Comment', backref='post', lazy='dynamic')

	#生成虚拟Post测试数据
	@staticmethod
	def generate_fake(count=100):
		from random import seed, randint
		import forgery_py
		seed()
		user_count = User.query.count()
		for i in range(count):
			u = User.query.offset(randint(0, user_count - 1)).first()
			p = Post(title=forgery_py.name.full_name(),
				body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
				timestamp=forgery_py.date.date(True),
				author=u)
			db.session.add(p)
			db.session.commit()
	#^^^生成虚拟Post测试数据

	#markdown 转义
	@staticmethod
	def on_changed_body(target, value, oldvalue, initiator):
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
				'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
				'h1', 'h2', 'h3', 'p']
		target.body_html = bleach.linkify(bleach.clean(
			markdown(value, output_format='html'),
			tags=allowed_tags, strip=True))
#自动识别并转义
db.event.listen(Post.body, 'set', Post.on_changed_body)


##评论
class Comment(db.Model):
	__tablename__ = 'comments'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
	disabled = db.Column(db.Boolean)
	author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

