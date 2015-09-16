from app import db
db.create_all()
Role.insert_roles()
Role.query.all()
User.generate_fake(100)
Post.generate_fake(100)
User.add_self_follows()