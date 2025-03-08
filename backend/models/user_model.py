class User:
    def __init__(self, uid, name, email):
        self.uid = uid
        self.name = name
        self.email = email

    def to_dict(self):
        return {"uid": self.uid, "name": self.name, "email": self.email}
