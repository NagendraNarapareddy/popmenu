from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType
import secrets

db = SQLAlchemy()

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    items = db.Column(MutableList.as_mutable(PickleType), default=list)
    access_token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), 
                         onupdate=db.func.now())
    
    def __init__(self, name, items=None):
        self.name = name
        self.items = items if items else []
        self.access_token = self._generate_token()
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'
    
    def _generate_token(self):
        """Generate a secure random access token"""
        return secrets.token_urlsafe(48)
    
    def add_item(self, item):
        """Add an item to the restaurant's menu"""
        if item not in self.items:
            self.items.append(item)
            db.session.commit()
    
    def remove_item(self, item):
        """Remove an item from the restaurant's menu"""
        if item in self.items:
            self.items.remove(item)
            db.session.commit()
    
    def refresh_token(self):
        """Generate a new access token"""
        self.access_token = self._generate_token()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'name': self.name,
            'items': self.items,
            'access_token': self.access_token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }