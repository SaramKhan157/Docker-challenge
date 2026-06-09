import os
from flask import Flask
from redis import Redis

app = Flask(__name__)

redis = Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
)


@app.route("/")
def index():
    return "<h1>Welcome to the CoderCo Containers Challenge!</h1>"


@app.route("/count")
def count():
    visits = redis.incr("visits")
    return f"<h1>Visit count: {visits}</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
