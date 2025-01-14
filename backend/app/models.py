from . import db
from datetime import datetime

class Reflection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10))  # 'morning' or 'evening'
    date = db.Column(db.DateTime, default=datetime.utcnow)
    priorities = db.Column(db.Text)
    intention = db.Column(db.Text)
    reflection = db.Column(db.Text)
    challenges = db.Column(db.Text)
    tomorrow = db.Column(db.Text)
    images = db.relationship('Image', backref='reflection', lazy=True)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    path = db.Column(db.String(255))
    reflection_id = db.Column(db.Integer, db.ForeignKey('reflection.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow) 