import hashlib
import uuid
from firebase_config import db


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = self.hash_password(password)
        self.user_id = str(uuid.uuid4())
        self.known_words = []
        self.unknown_words = []

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def save_to_firestore(self):
        user_ref = db.collection('users').document(self.username)
        user_ref.set({
            'username': self.username,
            'password': self.password,
            'user_id': self.user_id,
            'known_words': [],
            'unknown_words': []
        })

    @staticmethod
    def get_user(username):
        user_ref = db.collection('users').document(username).get()
        if user_ref.exists:
            return user_ref.to_dict()
        return None

    @staticmethod
    def authenticate(username, password):
        user = User.get_user(username)
        if user and user['password'] == User.hash_password(password):
            return True
        return False
