"""Database models for the Hello Game application."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class GameSubmission(db.Model):
    """Model for storing game name submissions."""

    __tablename__ = 'game_submissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<GameSubmission {self.name} at {self.submitted_at}>'

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'submitted_at': self.submitted_at.isoformat()
        }

    @classmethod
    def get_name_stats(cls):
        """Get statistics of name submissions."""
        # Query to get name counts
        name_counts = db.session.query(
            cls.name,
            db.func.count(cls.name).label('count')
        ).group_by(cls.name).order_by(db.func.count(cls.name).desc()).all()

        # Calculate statistics
        total_players = db.session.query(cls).count()
        unique_names = len(name_counts)
        most_popular = name_counts[0].name if name_counts else None

        # Format name data for frontend
        name_data = [
            {'name': name, 'count': count}
            for name, count in name_counts
        ]

        return {
            'total_players': total_players,
            'unique_names': unique_names,
            'most_popular': most_popular,
            'name_data': name_data
        }

    @classmethod
    def add_submission(cls, name):
        """Add a new name submission."""
        submission = cls(name=name.strip().title())
        db.session.add(submission)
        db.session.commit()
        return submission
