class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/reachout'  # Example database URI
    SECRET_KEY = 'your-secret-key'
    # You can add more configurations here as required
