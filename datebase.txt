from app import db
db.create_all()
Role.insert_roles()
Role.query.all()