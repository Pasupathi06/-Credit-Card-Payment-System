payload = jwt.decode(
    token,
    settings.jwt_secret_key,
    algorithms=["HS256"],
)