import os


DB_HOST = os.getenv("FC_DB_HOST", "localhost")
DB_USER = os.getenv("FC_DB_USER", "root")
DB_PASSWORD = os.getenv("FC_DB_PASSWORD", "")
DB_NAME = os.getenv("FC_DB_NAME", "fc_donation")

SECRET_KEY = os.getenv(
    "FC_SECRET_KEY",
    "change-this-secret-key-before-production"
)